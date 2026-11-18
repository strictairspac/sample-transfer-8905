import time,traceback,json
from pathlib import Path
from src.config.database import Session
from src.config.settings import ARTIFACT_DIR
from src.models.entities import Trial
from src.services.trials import queue
from src.services.concurrency import execute
while True:
    Path('/tmp/worker-heartbeat').touch()
    item=queue.blpop('locklab:queue',timeout=2)
    if not item: continue
    ident=int(item[1])
    try:
        result=execute(ident)
        Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True)
        Path(f'{ARTIFACT_DIR}/trial-{ident}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as e:
        traceback.print_exc()
        with Session() as db:
            obj=db.get(Trial,ident)
            if obj: obj.status='failed';obj.error=str(e);db.commit()
