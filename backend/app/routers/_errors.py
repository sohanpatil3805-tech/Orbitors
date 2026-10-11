from fastapi import HTTPException

from app.services import NotReady


def run(fn, *args, **kwargs):
    """Call a service function, turning its errors into HTTP responses."""
    try:
        return fn(*args, **kwargs)
    except (NotReady, FileNotFoundError) as e:          # live screening still loading / data or model missing
        raise HTTPException(status_code=503, detail=str(e))
    except KeyError as e:                               # unknown satellite, conjunction or event
        raise HTTPException(status_code=404, detail=e.args[0] if e.args else str(e))
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=422, detail=str(e))
