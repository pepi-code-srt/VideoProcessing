import unittest
import cv2
import numpy as np
from video_processor import process_frame, numpy_to_base64, get_confidence_threshold, process_video, draw_boxes_and_labels
from tracker import Tracker

class TestVideoProcessor(unittest.TestCase):

    def setUp(self):
        self.frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        self.tracker = Tracker()
        self.fps = 30
        self.confidence_threshold = 0.5

    def test_numpy_to_base64(self):
        base64_str = numpy_to_base64(self.frame)
        self.assertTrue(isinstance(base64_str, str))

    def test_get_confidence_threshold(self):
        self.assertEqual(get_confidence_threshold(0, 0.5), 0.5)
        self.assertEqual(get_confidence_threshold(10, 0.7), 0.7)

    def test_draw_boxes_and_labels(self):
        # Mocking YOLO result
        results = type('', (), {})()  # create a mock object
        results.boxes = [
            type('', (), {'cls': [0], 'conf': [0.9], 'xyxy': [[100, 100, 200, 200]]})(),
            type('', (), {'cls': [1], 'conf': [0.6], 'xyxy': [[300, 300, 400, 400]]})()
        ]
        annotated_frame = draw_boxes_and_labels(self.frame, results, self.tracker, self.confidence_threshold)
        self.assertIsNotNone(annotated_frame)

    def test_process_frame(self):
        frame_data = process_frame(self.frame, 0, self.fps, self.tracker, self.confidence_threshold)
        self.assertIn("frame", frame_data)
        self.assertIn("object_counts", frame_data)
        self.assertIn("segmented_images", frame_data)
        self.assertIn("unique_labels", frame_data)

    def test_process_video(self):
        # Create a temporary video file for testing
        filepath = 'test_video.mp4'
        cap = cv2.VideoCapture(filepath)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        result = process_video(filepath, None, self.confidence_threshold)
        self.assertIn("object_counts", result)
        self.assertIn("segmented_images", result)
        self.assertIn("total_frames", result)
        self.assertIn("fps", result)
        self.assertEqual(result["total_frames"], total_frames)
        self.assertEqual(result["fps"], fps)

if __name__ == '__main__':
    unittest.main()