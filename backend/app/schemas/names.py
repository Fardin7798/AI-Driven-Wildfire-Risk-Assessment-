from typing import Annotated

from pydantic import AfterValidator

from app.domain.names import humanize_gadm_name

# Region names as people read them ("Tamil Nadu"), not GADM's raw "TamilNadu".
ReadableName = Annotated[str, AfterValidator(humanize_gadm_name)]
