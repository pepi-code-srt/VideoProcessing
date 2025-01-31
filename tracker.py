class Tracker:
    def __init__(self):
        self.next_id = 0
        self.objects = {}

    def update(self, bbox, label):
        for object_id, (old_bbox, old_label) in self.objects.items():
            if self._is_same_object(bbox, old_bbox) and label == old_label:
                self.objects[object_id] = (bbox, label)
                return object_id
        self.next_id += 1
        self.objects[self.next_id] = (bbox, label)
        return self.next_id

    def _is_same_object(self, bbox1, bbox2):
        x1, y1, x2, y2 = bbox1
        xx1, yy1, xx2, yy2 = bbox2
        iou = self._iou(bbox1, bbox2)
        return iou > 0.5

    def _iou(self, bbox1, bbox2):
        x1, y1, x2, y2 = bbox1
        xx1, yy1, xx2, yy2 = bbox2
        ix1 = max(x1, xx1)
        iy1 = max(y1, yy1)
        ix2 = min(x2, xx2)
        iy2 = min(y2, yy2)
        iw = max(ix2 - ix1, 0)
        ih = max(iy2 - iy1, 0)
        intersection = iw * ih
        area1 = (x2 - x1) * (y2 - y1)
        area2 = (xx2 - xx1) * (yy2 - yy1)
        union = area1 + area2 - intersection
        return intersection / union
