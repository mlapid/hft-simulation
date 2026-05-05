from pydantic import BaseModel, Field, field_validator


class ConnectorMessage(BaseModel):
    session_id: str = Field(alias='session_id', description='Uuid4 session ID')
    channel: str = Field(alias='channel', description='The name of the channel')
    data: dict = Field(alias='data', description='The data of the message')
    recv_timestamp: int = Field(alias='recv_timestamp', description='The timestamp of the message reception in milliseconds')
    offset: int = Field(alias='offset', description='The offset of the message in milliseconds')

    @field_validator('recv_timestamp', mode='before')
    @classmethod
    def convert_recv_timestamp_to_milliseconds(cls, v: int) -> int:
        match len(str(v)):
            case 13:
                return v
            case 16:
                return int(v / 1e3)
            case 19:
                return int(v / 1e6)
            case _:
                raise ValueError(f'Invalid recv_timestamp: {v} with {len(str(v))} digits.')