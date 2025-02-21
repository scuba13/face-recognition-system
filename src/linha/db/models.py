from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

@dataclass
class Employee:
    employee_id: str
    name: str
    face_encoding: List[float]
    created_at: datetime

    def to_dict(self) -> Dict:
        return {
            'employee_id': self.employee_id,
            'name': self.name,
            'face_encoding': self.face_encoding,
            'created_at': self.created_at
        }

@dataclass
class BatchDetection:
    line_id: str
    batch_path: str
    timestamp: datetime
    capture_datetime: datetime
    processed_at: datetime
    processor_id: str
    total_images: int
    processing_time: float
    total_faces_detected: int
    total_faces_recognized: int
    total_faces_unknown: int
    unique_people_recognized: int
    unique_people_unknown: int
    detections: List[Dict]

    def to_dict(self) -> Dict:
        return {
            'line_id': self.line_id,
            'batch_path': self.batch_path,
            'timestamp': self.timestamp,
            'capture_datetime': self.capture_datetime,
            'processed_at': self.processed_at,
            'processor_id': self.processor_id,
            'total_images': self.total_images,
            'processing_time': self.processing_time,
            'total_faces_detected': self.total_faces_detected,
            'total_faces_recognized': self.total_faces_recognized,
            'total_faces_unknown': self.total_faces_unknown,
            'unique_people_recognized': self.unique_people_recognized,
            'unique_people_unknown': self.unique_people_unknown,
            'detections': self.detections
        } 