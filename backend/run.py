"""Convenience entrypoint: python run.py starts uvicorn on port 8000.

Use this if you don't want to remember the uvicorn incantation:
    python run.py
or
    uvicorn app.main:app --reload --port 8000
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
