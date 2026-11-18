"""Keyset review sessions.

A review ("查阅") freezes the transfer requests together with the sample
quantities at one instant: the snapshot rows are inserted in the same
transaction that creates the session, so concurrent registrations and quantity
changes cannot interleave between the two reads. Paging advances a cursor
inside short transactions (row-level locks make it safe under concurrent
requests); idle sessions hold no database connection. An expired session
rejects old pages and its retained rows are released lazily and by a sweeper.
"""
import threading
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from src.config.database import Session
from src.config.settings import REVIEW_TTL_SECONDS, REVIEW_SWEEP_SECONDS
from src.constants.enums import REVIEW_STATES
from src.models.entities import Audit, ReviewSession, ReviewItem, Transfer, Sample
from src.utils.serialization import record

def _now():
    return datetime.now(timezone.utc)

def _payload(session):
    data = record(session)
    data['expires_at'] = session.expires_at.isoformat()
    data['created_at'] = session.created_at.isoformat()
    return data

def create_session(db, data, user):
    ttl = data.ttl_seconds or REVIEW_TTL_SECONDS
    now = _now()
    session = ReviewSession(code=data.code, page_size=data.page_size, total=0,
                            last_position=0, status=REVIEW_STATES[0],
                            created_at=now, expires_at=now + timedelta(seconds=ttl))
    db.add(session)
    try:
        db.flush()
        # Single read-committed statement joins both tables at one instant; all
        # snapshot rows and the session header commit together or roll back together.
        rows = db.execute(
            select(Transfer.id, Transfer.code, Transfer.destination, Transfer.quantity,
                   Sample.code, Sample.quantity)
            .join(Sample, Sample.id == Transfer.sample_id)
            .order_by(Transfer.id)
        ).all()
        items = [ReviewItem(session_id=session.id, position=pos,
                            transfer_id=row[0], transfer_code=row[1], destination=row[2],
                            transfer_quantity=row[3], sample_code=row[4], sample_quantity=row[5])
                 for pos, row in enumerate(rows, start=1)]
        db.add_all(items)
        session.total = len(items)
        first_page = [record(x) for x in db.scalars(
            select(ReviewItem).where(ReviewItem.session_id == session.id)
            .order_by(ReviewItem.position).limit(session.page_size))]
        # Creation also serves page 1: advance the cursor in the same transaction
        # so a later page call can never re-serve the first page.
        session.last_position = len(first_page)
        db.add(Audit(actor=user.email, action='发起移交复核查阅 ' + data.code))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '查阅编号已存在，请换一个编号重试')
    db.refresh(session)
    result = _payload(session)
    result['first_page'] = first_page
    return result

def get_page(db, session_id, cursor):
    now = _now()
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, '查阅不存在或留存数据已释放')
    if session.status != REVIEW_STATES[0] or session.expires_at <= now:
        _release(db, session, REVIEW_STATES[1])
        db.commit()
        raise HTTPException(410, '查阅已到期，旧页不再可用，请重新发起查阅')
    if cursor != session.last_position:
        raise HTTPException(409, '页码游标已变化，请使用返回的 next_cursor 顺序翻页，避免漏读或重复')
    # Lock the header row for the cursor advance: concurrent page requests
    # serialize, so exactly one wins at each position (no lost update, no dup).
    # populate_existing() forces re-reading the winner's committed cursor from
    # the database instead of the session identity map's stale in-memory copy.
    locked = db.scalar(select(ReviewSession).where(ReviewSession.id == session_id)
                       .with_for_update().execution_options(populate_existing=True))
    if locked.status != REVIEW_STATES[0] or locked.expires_at <= _now():
        _release(db, locked, REVIEW_STATES[1])
        db.commit()
        raise HTTPException(410, '查阅已到期，旧页不再可用，请重新发起查阅')
    if cursor != locked.last_position:
        db.rollback()
        raise HTTPException(409, '页码游标已变化，请使用返回的 next_cursor 顺序翻页，避免漏读或重复')
    items = [record(x) for x in db.scalars(
        select(ReviewItem)
        .where(ReviewItem.session_id == session_id, ReviewItem.position > cursor)
        .order_by(ReviewItem.position)
        .limit(locked.page_size))]
    next_position = cursor + len(items)
    locked.last_position = next_position
    db.commit()
    return {'session_id': session_id, 'cursor': cursor, 'next_cursor': next_position,
            'page_size': locked.page_size, 'total': locked.total,
            'has_next': next_position < locked.total, 'items': items}

def get_status(db, session_id):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, '查阅不存在或留存数据已释放')
    if session.status == REVIEW_STATES[0] and session.expires_at <= _now():
        _release(db, session, REVIEW_STATES[1])
        db.commit()
    return _payload(session)

def close(db, session_id, user):
    session = db.get(ReviewSession, session_id)
    if not session:
        raise HTTPException(404, '查阅不存在或留存数据已释放')
    if session.status == REVIEW_STATES[0]:
        _release(db, session, REVIEW_STATES[2])
        db.add(Audit(actor=user.email, action='结束移交复核查阅 ' + session.code))
        db.commit()
    return _payload(session)

def _release(db, session, status):
    """Delete retained snapshot rows and mark the header, in one transaction."""
    db.execute(delete(ReviewItem).where(ReviewItem.session_id == session.id))
    session.status = status

def sweep_expired():
    """One cleanup pass. SKIP LOCKED means a page being read is never touched:
    readers always observe either a whole page or an expiry error, never a half page."""
    with Session() as db:
        now = _now()
        expired = db.scalars(
            select(ReviewSession)
            .where(ReviewSession.status == REVIEW_STATES[0], ReviewSession.expires_at <= now)
            .with_for_update(skip_locked=True)).all()
        for session in expired:
            db.execute(delete(ReviewItem).where(ReviewItem.session_id == session.id))
            session.status = REVIEW_STATES[1]
        if expired:
            db.commit()
        return len(expired)

def _sweeper_loop():
    timer = threading.Event()
    while not timer.wait(REVIEW_SWEEP_SECONDS):
        try:
            sweep_expired()
        except Exception:
            import logging
            logging.exception('review sweep failed; will retry next tick')

def start_sweeper():
    threading.Thread(target=_sweeper_loop, name='review-sweeper', daemon=True).start()
