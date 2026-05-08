from pydantic import BaseModel


class ModuleSignal(BaseModel):
    module_id: str
    value: float
    status: str
