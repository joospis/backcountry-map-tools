from typing import NamedTuple

class BoundingBox(NamedTuple):
    """
    Represents a WGS84 bounding box.
    
    Attributes:
        xmin (float): Minimum longitude (West)
        ymin (float): Minimum latitude (South)
        xmax (float): Maximum longitude (East)
        ymax (float): Maximum latitude (North)
    """
    xmin: float
    ymin: float
    xmax: float
    ymax: float