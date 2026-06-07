from pydantic import BaseModel, Field, field_validator


class ConnectorMessage(BaseModel):
    session_id: str = Field(description='Uuid4 session ID')
    channel: str = Field(description='The name of the channel')
    data: dict = Field(description='The data of the message')
    timestamp: int = Field(description='The timestamp of the message reception in milliseconds')
    offset: int = Field(description='The offset of the message in milliseconds')
    heartbeat_age: int = Field(description='The age of the heartbeat in milliseconds')