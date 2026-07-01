from fastapi import APIRouter, HTTPException

from app import macro_store, schemas

router = APIRouter(prefix="/jarvis/macros", tags=["macros"])


@router.get("", response_model=list[schemas.MacroView])
def list_macros():
    return [
        schemas.MacroView(name=name, apps=apps)
        for name, apps in macro_store.list_macros().items()
    ]


@router.get("/{name}", response_model=schemas.MacroView)
def get_macro(name: str):
    apps = macro_store.get_macro(name)
    if apps is None:
        raise HTTPException(status_code=404, detail="No such macro")
    return schemas.MacroView(name=name, apps=apps)


@router.post("", response_model=schemas.MacroView, status_code=201)
def create_macro(body: schemas.MacroCreate):
    apps = body.model_dump()["apps"]
    if not macro_store.create_macro(body.name, apps):
        raise HTTPException(status_code=409, detail="Macro already exists")
    return schemas.MacroView(name=body.name, apps=apps)


@router.put("/{name}", response_model=schemas.MacroView)
def update_macro(name: str, body: schemas.MacroUpdate):
    apps = body.model_dump()["apps"]
    macro_store.upsert_macro(name, apps)
    return schemas.MacroView(name=name, apps=apps)


@router.delete("/{name}", status_code=204, response_model=None)
def delete_macro(name: str) -> None:
    if not macro_store.delete_macro(name):
        raise HTTPException(status_code=404, detail="No such macro")
