from pydantic import BaseModel


# --Schemas--

class Address(BaseModel):
    address_line1: str
    address_line2: str
    state: str
    country: str
    zip: str


# --Requests--

# --Response--

class CommonResponse(BaseModel):
    message: str


