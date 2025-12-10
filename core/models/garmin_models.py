from typing import TypedDict, Optional


class GarminActivityType(TypedDict):
    typeKey: Optional[str]
    typeId: Optional[int]


class GarminActivity(TypedDict):
    activityId: int
    activityName: Optional[str]
    startTimeLocal: Optional[str]
    activityType: GarminActivityType


class GarminHole(TypedDict):
    holeNumber: int
    par: Optional[int]
    score: Optional[int]
    putts: Optional[int]
    fairwayHit: Optional[bool]
    greenInRegulation: Optional[bool]
    driveDistance: Optional[float]