# # # vim: expandtab:ts=4:sw=4
# # from __future__ import division, print_function, absolute_import

# import argparse
# import os

# import cv2
# import numpy as np

# from application_util import preprocessing
# from application_util import visualization
# from deep_sort import nn_matching
# from deep_sort.detection import Detection
# from deep_sort.tracker import Tracker
# from opts import opt


# def gather_sequence_info(sequence_dir, detection_file):
#     """Gather sequence information, such as image filenames, detections,
#     groundtruth (if available).

#     Parameters
#     ----------
#     sequence_dir : str
#         Path to the MOTChallenge sequence directory.
#     detection_file : str
#         Path to the detection file.

#     Returns
#     -------
#     Dict
#         A dictionary of the following sequence information:

#         * sequence_name: Name of the sequence
#         * image_filenames: A dictionary that maps frame indices to image
#           filenames.
#         * detections: A numpy array of detections in MOTChallenge format.
#         * groundtruth: A numpy array of ground truth in MOTChallenge format.
#         * image_size: Image size (height, width).
#         * min_frame_idx: Index of the first frame.
#         * max_frame_idx: Index of the last frame.

#     """
#     image_dir = os.path.join(sequence_dir, "img1")
#     image_filenames = {
#         int(os.path.splitext(f)[0]): os.path.join(image_dir, f)
#         for f in os.listdir(image_dir)}
#     groundtruth_file = os.path.join(sequence_dir, "gt/gt.txt")

#     detections = None
#     if detection_file is not None:
#         detections = np.load(detection_file)
#     groundtruth = None
#     if os.path.exists(groundtruth_file):
#         groundtruth = np.loadtxt(groundtruth_file, delimiter=',')

#     if len(image_filenames) > 0:
#         image = cv2.imread(next(iter(image_filenames.values())),
#                            cv2.IMREAD_GRAYSCALE)
#         image_size = image.shape
#     else:
#         image_size = None

#     if len(image_filenames) > 0:
#         min_frame_idx = min(image_filenames.keys())
#         max_frame_idx = max(image_filenames.keys())
#     else:
#         min_frame_idx = int(detections[:, 0].min())
#         max_frame_idx = int(detections[:, 0].max())

#     info_filename = os.path.join(sequence_dir, "seqinfo.ini")
#     if os.path.exists(info_filename):
#         with open(info_filename, "r") as f:
#             line_splits = [l.split('=') for l in f.read().splitlines()[1:]]
#             info_dict = dict(
#                 s for s in line_splits if isinstance(s, list) and len(s) == 2)

#         update_ms = 1000 / int(info_dict["frameRate"])
#     else:
#         update_ms = None

#     feature_dim = detections.shape[1] - 10 if detections is not None else 0
#     seq_info = {
#         "sequence_name": os.path.basename(sequence_dir),
#         "image_filenames": image_filenames,
#         "detections": detections,
#         "groundtruth": groundtruth,
#         "image_size": image_size,
#         "min_frame_idx": min_frame_idx,
#         "max_frame_idx": max_frame_idx,
#         "feature_dim": feature_dim,
#         "update_ms": update_ms
#     }
#     return seq_info


# def create_detections(detection_mat, frame_idx, min_height=0):
#     """Create detections for given frame index from the raw detection matrix.

#     Parameters
#     ----------
#     detection_mat : ndarray
#         Matrix of detections. The first 10 columns of the detection matrix are
#         in the standard MOTChallenge detection format. In the remaining columns
#         store the feature vector associated with each detection.
#     frame_idx : int
#         The frame index.
#     min_height : Optional[int]
#         A minimum detection bounding box height. Detections that are smaller
#         than this value are disregarded.

#     Returns
#     -------
#     List[tracker.Detection]
#         Returns detection responses at given frame index.

#     """
#     frame_indices = detection_mat[:, 0].astype(int)
#     mask = frame_indices == frame_idx

#     detection_list = []
#     for row in detection_mat[mask]:
#         bbox, confidence, feature = row[2:6], row[6], row[10:]
#         if bbox[3] < min_height:
#             continue
#         detection_list.append(Detection(bbox, confidence, feature))
#     return detection_list


# def run(sequence_dir, detection_file, output_file, min_confidence,
#         nms_max_overlap, min_detection_height, max_cosine_distance,
#         nn_budget, display):
#     """Run multi-target tracker on a particular sequence.

#     Parameters
#     ----------
#     sequence_dir : str
#         Path to the MOTChallenge sequence directory.
#     detection_file : str
#         Path to the detections file.
#     output_file : str
#         Path to the tracking output file. This file will contain the tracking
#         results on completion.
#     min_confidence : float
#         Detection confidence threshold. Disregard all detections that have
#         a confidence lower than this value.
#     nms_max_overlap: float
#         Maximum detection overlap (non-maxima suppression threshold).
#     min_detection_height : int
#         Detection height threshold. Disregard all detections that have
#         a height lower than this value.
#     max_cosine_distance : float
#         Gating threshold for cosine distance metric (object appearance).
#     nn_budget : Optional[int]
#         Maximum size of the appearance descriptor gallery. If None, no budget
#         is enforced.
#     display : bool
#         If True, show visualization of intermediate tracking results.

#     """
#     seq_info = gather_sequence_info(sequence_dir, detection_file)
#     metric = nn_matching.NearestNeighborDistanceMetric(
#         'cosine',
#         max_cosine_distance,
#         nn_budget
#     )
#     tracker = Tracker(metric)
#     results = []

#     def frame_callback(vis, frame_idx):
#         # print("Processing frame %05d" % frame_idx)

#         # Load image and generate detections.
#         detections = create_detections(
#             seq_info["detections"], frame_idx, min_detection_height)
#         detections = [d for d in detections if d.confidence >= min_confidence]

#         # Run non-maxima suppression.
#         boxes = np.array([d.tlwh for d in detections])
#         scores = np.array([d.confidence for d in detections])
#         indices = preprocessing.non_max_suppression(
#             boxes, nms_max_overlap, scores)
#         detections = [detections[i] for i in indices]

#         # Update tracker.
#         if opt.ECC:
#             tracker.camera_update(sequence_dir.split('/')[-1], frame_idx)

#         tracker.predict()
#         tracker.update(detections)

#         # Update visualization.
#         if display:
#             image = cv2.imread(
#                 seq_info["image_filenames"][frame_idx], cv2.IMREAD_COLOR)
#             vis.set_image(image.copy())
#             vis.draw_detections(detections)
#             vis.draw_trackers(tracker.tracks)

#         # Store results.
#         for track in tracker.tracks:
#             if not track.is_confirmed() or track.time_since_update > 1:
#                 continue
#             bbox = track.to_tlwh()
#             results.append([
#                     frame_idx, track.track_id, bbox[0], bbox[1], bbox[2], bbox[3]])

#     # Run tracker.
#     if display:
#         visualizer = visualization.Visualization(seq_info, update_ms=5)
#     else:
#         visualizer = visualization.NoVisualization(seq_info)
#     visualizer.run(frame_callback)

#     # Store results.
#     f = open(output_file, 'w')
#     for row in results:
#         print('%d,%d,%.2f,%.2f,%.2f,%.2f,1,-1,-1,-1' % (
#             row[0], row[1], row[2], row[3], row[4], row[5]),file=f)

# def bool_string(input_string):
#     if input_string not in {"True","False"}:
#         raise ValueError("Please Enter a valid Ture/False choice")
#     else:
#         return (input_string == "True")

# def parse_args():
#     """ Parse command line arguments.
#     """
#     parser = argparse.ArgumentParser(description="Deep SORT")
#     parser.add_argument(
#         "--sequence_dir", help="Path to MOTChallenge sequence directory",
#         default=None, required=True)
#     parser.add_argument(
#         "--detection_file", help="Path to custom detections.", default=None,
#         required=True)
#     parser.add_argument(
#         "--output_file", help="Path to the tracking output file. This file will"
#         " contain the tracking results on completion.",
#         default="/tmp/hypotheses.txt")
#     parser.add_argument(
#         "--min_confidence", help="Detection confidence threshold. Disregard "
#         "all detections that have a confidence lower than this value.",
#         default=0.8, type=float)
#     parser.add_argument(
#         "--min_detection_height", help="Threshold on the detection bounding "
#         "box height. Detections with height smaller than this value are "
#         "disregarded", default=0, type=int)
#     parser.add_argument(
#         "--nms_max_overlap",  help="Non-maxima suppression threshold: Maximum "
#         "detection overlap.", default=1.0, type=float)
#     parser.add_argument(
#         "--max_cosine_distance", help="Gating threshold for cosine distance "
#         "metric (object appearance).", type=float, default=0.2)
#     parser.add_argument(
#         "--nn_budget", help="Maximum size of the appearance descriptors "
#         "gallery. If None, no budget is enforced.", type=int, default=None)
#     parser.add_argument(
#         "--display", help="Show intermediate tracking results",
#         default=True, type=bool_string)
#     return parser.parse_args()


# if __name__ == "__main__":
#     args = parse_args()
#     run(
#         args.sequence_dir, args.detection_file, args.output_file,
#         args.min_confidence, args.nms_max_overlap, args.min_detection_height,
#         args.max_cosine_distance, args.nn_budget, args.display)
# vim: expandtab:ts=4:sw=4
# from __future__ import division, print_function, absolute_import

# import argparse
# import os

# import cv2
# import numpy as np

# from application_util import preprocessing
# from application_util import visualization
# from deep_sort import nn_matching
# from deep_sort.detection import Detection
# from deep_sort.tracker import Tracker
# from opts import opt


# def gather_sequence_info(sequence_dir, detection_file):
#     """Gather sequence information, such as image filenames, detections,
#     groundtruth (if available).

#     Parameters
#     ----------
#     sequence_dir : str
#         Path to the MOTChallenge sequence directory.
#     detection_file : str
#         Path to the detection file.

#     Returns
#     -------
#     Dict
#         A dictionary of the following sequence information:

#         * sequence_name: Name of the sequence
#         * image_filenames: A dictionary that maps frame indices to image
#           filenames.
#         * detections: A numpy array of detections in MOTChallenge format.
#         * groundtruth: A numpy array of ground truth in MOTChallenge format.
#         * image_size: Image size (height, width).
#         * min_frame_idx: Index of the first frame.
#         * max_frame_idx: Index of the last frame.

#     """
#     image_dir = os.path.join(sequence_dir, "img1")
#     # image_filenames = {
#     #     int(os.path.splitext(f)[0]): os.path.join(image_dir, f)
#     #     for f in os.listdir(image_dir)}
#     # groundtruth_file = os.path.join(sequence_dir, "gt/gt.txt")
#     image_filenames = {
#         int(os.path.splitext(f)[0]): os.path.join(image_dir, f)
#         for f in os.listdir(image_dir) if os.path.splitext(f)[0].isdigit()
#     }
#     groundtruth_file = os.path.join(sequence_dir, "gt/gt.txt")
#     print(f"groundtruth_file {groundtruth_file}") # /home/uav23/Downloads/data/MOTChallenge/MOT17/test/MOT17-01-FRCNN/gt/gt.txt
#     detections = None
#     if detection_file is not None:
#         detections = np.load(detection_file)
#     groundtruth = None
#     if os.path.exists(groundtruth_file):
#         groundtruth = np.loadtxt(groundtruth_file, delimiter=',')

#     if len(image_filenames) > 0:
#         image = cv2.imread(next(iter(image_filenames.values())),
#                            cv2.IMREAD_GRAYSCALE)
#         image_size = image.shape
#     else:
#         image_size = None

#     if len(image_filenames) > 0:
#         min_frame_idx = min(image_filenames.keys())
#         max_frame_idx = max(image_filenames.keys())
#     else:
#         min_frame_idx = int(detections[:, 0].min())
#         max_frame_idx = int(detections[:, 0].max())

#     info_filename = os.path.join(sequence_dir, "seqinfo.ini")
#     if os.path.exists(info_filename):
#         with open(info_filename, "r") as f:
#             line_splits = [l.split('=') for l in f.read().splitlines()[1:]]
#             info_dict = dict(
#                 s for s in line_splits if isinstance(s, list) and len(s) == 2)

#         update_ms = 1000 / int(info_dict["frameRate"])
#     else:
#         update_ms = None

#     feature_dim = detections.shape[1] - 10 if detections is not None else 0
#     seq_info = {
#         "sequence_name": os.path.basename(sequence_dir),
#         "image_filenames": image_filenames,
#         "detections": detections,
#         "groundtruth": groundtruth,
#         "image_size": image_size,
#         "min_frame_idx": min_frame_idx,
#         "max_frame_idx": max_frame_idx,
#         "feature_dim": feature_dim,
#         "update_ms": update_ms
#     }
#     return seq_info


# def create_detections(detection_mat, frame_idx, min_height=0):
#     """Create detections for given frame index from the raw detection matrix.

#     Parameters
#     ----------
#     detection_mat : ndarray
#         Matrix of detections. The first 10 columns of the detection matrix are
#         in the standard MOTChallenge detection format. In the remaining columns
#         store the feature vector associated with each detection.
#     frame_idx : int
#         The frame index.
#     min_height : Optional[int]
#         A minimum detection bounding box height. Detections that are smaller
#         than this value are disregarded.

#     Returns
#     -------
#     List[tracker.Detection]
#         Returns detection responses at given frame index.

#     """
#     frame_indices = detection_mat[:, 0].astype(int)
#     mask = frame_indices == frame_idx

#     detection_list = []
#     for row in detection_mat[mask]:
#         bbox, confidence, feature = row[2:6], row[6], row[10:]
#         if bbox[3] < min_height:
#             continue
#         detection_list.append(Detection(bbox, confidence, feature))
#     return detection_list


# def run(sequence_dir, detection_file, output_file, min_confidence,
#         nms_max_overlap, min_detection_height, max_cosine_distance,
#         nn_budget, display):
#     """Run multi-target tracker on a particular sequence.

#     Parameters
#     ----------
#     sequence_dir : str
#         Path to the MOTChallenge sequence directory.
#     detection_file : str
#         Path to the detections file.
#     output_file : str
#         Path to the tracking output file. This file will contain the tracking
#         results on completion.
#     min_confidence : float
#         Detection confidence threshold. Disregard all detections that have
#         a confidence lower than this value.
#     nms_max_overlap: float
#         Maximum detection overlap (non-maxima suppression threshold).
#     min_detection_height : int
#         Detection height threshold. Disregard all detections that have
#         a height lower than this value.
#     max_cosine_distance : float
#         Gating threshold for cosine distance metric (object appearance).
#     nn_budget : Optional[int]
#         Maximum size of the appearance descriptor gallery. If None, no budget
#         is enforced.
#     display : bool
#         If True, show visualization of intermediate tracking results.

#     """
#     seq_info = gather_sequence_info(sequence_dir, detection_file)
#     metric = nn_matching.NearestNeighborDistanceMetric(
#         'cosine',
#         max_cosine_distance,
#         nn_budget
#     )
#     tracker = Tracker(metric)
#     results = []

#     def frame_callback(vis, frame_idx):
#         # print("Processing frame %05d" % frame_idx)

#         # Load image and generate detections.
#         detections = create_detections(
#             seq_info["detections"], frame_idx, min_detection_height)
#         detections = [d for d in detections if d.confidence >= min_confidence]
        
#         # Run non-maxima suppression.
#         boxes = np.array([d.tlwh for d in detections])
#         scores = np.array([d.confidence for d in detections])
#         indices = preprocessing.non_max_suppression(
#             boxes, nms_max_overlap, scores)
#         detections = [detections[i] for i in indices]

#         # Update tracker.
#         if opt.ECC:
#             tracker.camera_update(sequence_dir.split('/')[-1], frame_idx)

#         tracker.predict()
#         tracker.update(detections)

#         # Update visualization.
#         if display:
#             image = cv2.imread(
#                 seq_info["image_filenames"][frame_idx], cv2.IMREAD_COLOR)
#             vis.set_image(image.copy())
#             vis.draw_detections(detections)
#             vis.draw_trackers(tracker.tracks)

#         # Store results.
#         for track in tracker.tracks:
#             if not track.is_confirmed() or track.time_since_update > 1:
#                 continue
#             bbox = track.to_tlwh()
#             results.append([
#                     frame_idx, track.track_id, bbox[0], bbox[1], bbox[2], bbox[3]])

#     # Run tracker.
#     if display:
#         visualizer = visualization.Visualization(seq_info, update_ms=5)
#     else:
#         visualizer = visualization.NoVisualization(seq_info)
#     visualizer.run(frame_callback)

#     # Store results.
#     f = open(output_file, 'w')
#     for row in results:
#         print('%d,%d,%.2f,%.2f,%.2f,%.2f,1,-1,-1,-1' % (
#             row[0], row[1], row[2], row[3], row[4], row[5]),file=f)

# def bool_string(input_string):
#     if input_string not in {"True","False"}:
#         raise ValueError("Please Enter a valid Ture/False choice")
#     else:
#         return (input_string == "True")

# def parse_args():
#     """ Parse command line arguments.
#     """
#     parser = argparse.ArgumentParser(description="Deep SORT")
#     parser.add_argument(
#         "--sequence_dir", help="Path to MOTChallenge sequence directory",
#         default=None, required=True)
#     parser.add_argument(
#         "--detection_file", help="Path to custom detections.", default=None,
#         required=True)
#     parser.add_argument(
#         "--output_file", help="Path to the tracking output file. This file will"
#         " contain the tracking results on completion.",
#         default="/tmp/hypotheses.txt")
#     parser.add_argument(
#         "--min_confidence", help="Detection confidence threshold. Disregard "
#         "all detections that have a confidence lower than this value.",
#         default=0.8, type=float)
#     parser.add_argument(
#         "--min_detection_height", help="Threshold on the detection bounding "
#         "box height. Detections with height smaller than this value are "
#         "disregarded", default=0, type=int)
#     parser.add_argument(
#         "--nms_max_overlap",  help="Non-maxima suppression threshold: Maximum "
#         "detection overlap.", default=1.0, type=float)
#     parser.add_argument(
#         "--max_cosine_distance", help="Gating threshold for cosine distance "
#         "metric (object appearance).", type=float, default=0.2)
#     parser.add_argument(
#         "--nn_budget", help="Maximum size of the appearance descriptors "
#         "gallery. If None, no budget is enforced.", type=int, default=None)
#     parser.add_argument(
#         "--display", help="Show intermediate tracking results",
#         default=True, type=bool_string)
#     return parser.parse_args()


# if __name__ == "__main__":
#     args = parse_args()
#     run(
#         args.sequence_dir, args.detection_file, args.output_file,
#         args.min_confidence, args.nms_max_overlap, args.min_detection_height,
#         args.max_cosine_distance, args.nn_budget, args.display)



# from __future__ import division, print_function, absolute_import

import argparse
import os

import cv2
import numpy as np

from application_util import preprocessing
from application_util import visualization
from deep_sort import nn_matching
from deep_sort.detection import Detection
from deep_sort.tracker import Tracker
from opts import opt


def gather_sequence_info(sequence_dir, detection_file):
    image_dir = os.path.join(sequence_dir, "img1")
    image_filenames = {int(os.path.splitext(f)[0]): os.path.join(image_dir, f) for f in os.listdir(image_dir) if os.path.splitext(f)[0].isdigit()}
    groundtruth_file = os.path.join(sequence_dir, "gt/gt.txt")
    detections = np.load(detection_file) if detection_file is not None else None
    groundtruth = np.loadtxt(groundtruth_file, delimiter=',') if os.path.exists(groundtruth_file) else None
    image_size = cv2.imread(next(iter(image_filenames.values())), cv2.IMREAD_GRAYSCALE).shape if len(image_filenames) > 0 else None
    min_frame_idx = min(image_filenames.keys()) if len(image_filenames) > 0 else int(detections[:, 0].min())
    max_frame_idx = max(image_filenames.keys()) if len(image_filenames) > 0 else int(detections[:, 0].max())
    feature_dim = detections.shape[1] - 10 if detections is not None else 0
    seq_info = {
        "sequence_name": os.path.basename(sequence_dir),
        "image_filenames": image_filenames,
        "detections": detections,
        "groundtruth": groundtruth,
        "image_size": image_size,
        "min_frame_idx": min_frame_idx,
        "max_frame_idx": max_frame_idx,
        "feature_dim": feature_dim
    }
    return seq_info

def select_bounding_boxes(frame):
    boxes = []
    current_box = []
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            current_box[:] = [x, y, x, y]
        elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_LBUTTON:
            current_box[2:] = [x, y]
        elif event == cv2.EVENT_LBUTTONUP:
            boxes.append((min(current_box[0], current_box[2]),
                          min(current_box[1], current_box[3]),
                          abs(current_box[2] - current_box[0]),
                          abs(current_box[3] - current_box[1])))
            current_box[:] = []
    cv2.namedWindow("Image")
    cv2.setMouseCallback("Image", mouse_callback)
    while True:
        img = frame.copy()
        if current_box:
            cv2.rectangle(img, (current_box[0], current_box[1]), (current_box[2], current_box[3]), (0, 255, 0), 2)
        for box in boxes:
            cv2.rectangle(img, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (0, 255, 0), 2)
        cv2.imshow("Image", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()
    return boxes

def run(sequence_dir, detection_file, output_file, min_confidence, nms_max_overlap, min_detection_height, max_cosine_distance, nn_budget, display):
    seq_info = gather_sequence_info(sequence_dir, detection_file)
    metric = nn_matching.NearestNeighborDistanceMetric('cosine', max_cosine_distance, nn_budget)
    tracker = Tracker(metric)
    results = []
    first_frame_path = seq_info["image_filenames"][min(seq_info["image_filenames"].keys())]
    first_frame = cv2.imread(first_frame_path, cv2.IMREAD_COLOR)
    initial_boxes = select_bounding_boxes(first_frame)
    for box in initial_boxes:
        tracker.update([Detection(box, 1.0, np.array([]))])
        
    def frame_callback(vis, frame_idx):
        if frame_idx == 0:
            return
        image = cv2.imread(seq_info["image_filenames"][frame_idx], cv2.IMREAD_COLOR)
        tracker.predict()
        tracker.update([Detection(box, 1.0, np.array([])) for box in initial_boxes])
        if display:
            vis.set_image(image.copy())
            vis.draw_trackers(tracker.tracks)
        for track in tracker.tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue
            bbox = track.to_tlwh()
            results.append([frame_idx, track.track_id, bbox[0], bbox[1], bbox[2], bbox[3]])
            print(results)
    if display:
        visualizer = visualization.Visualization(seq_info, update_ms=5)
        visualizer.run(frame_callback)
    with open(output_file, 'w') as f:
        for row in results:
            print('%d,%d,%.2f,%.2f,%.2f,%.2f,1,-1,-1,-1' % (
                row[0], row[1], row[2], row[3], row[4], row[5]), file=f)

def bool_string(input_string):
    if input_string not in {"True","False"}:
        raise ValueError("Please Enter a valid Ture/False choice")
    else:
        return (input_string == "True")

def parse_args():
    parser = argparse.ArgumentParser(description="Deep SORT")
    parser.add_argument("--sequence_dir", help="Path to MOTChallenge sequence directory", required=True)
    parser.add_argument("--detection_file", help="Path to custom detections.", required=True)
    parser.add_argument("--output_file", help="Path to the tracking output file.", default="/tmp/hypotheses.txt")
    parser.add_argument("--min_confidence", help="Detection confidence threshold.", default=0.8, type=float)
    parser.add_argument("--min_detection_height", help="Threshold on the detection bounding box height.", default=0, type=int)
    parser.add_argument("--nms_max_overlap", help="Non-maxima suppression threshold.", default=1.0, type=float)
    parser.add_argument("--max_cosine_distance", help="Gating threshold for cosine distance metric.", type=float, default=0.2)
    parser.add_argument("--nn_budget", help="Maximum size of the appearance descriptors gallery.", type=int, default=None)
    parser.add_argument("--display", help="Show intermediate tracking results", default=True, type=bool_string)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    run(
        args.sequence_dir, args.detection_file, args.output_file,
        args.min_confidence, args.nms_max_overlap, args.min_detection_height,
        args.max_cosine_distance, args.nn_budget, args.display)


# from __future__ import division, print_function, absolute_import

# import argparse
# import os
# import cv2
# import numpy as np

# from application_util import preprocessing
# from application_util import visualization
# from deep_sort import nn_matching
# from deep_sort.detection import Detection
# from deep_sort.tracker import Tracker
# from opts import opt

# def gather_sequence_info(sequence_dir, detection_file):
#     image_dir = os.path.join(sequence_dir, "img1")
#     image_filenames = {
#         int(os.path.splitext(f)[0]): os.path.join(image_dir, f)
#         for f in os.listdir(image_dir) if os.path.splitext(f)[0].isdigit()
#     }
#     groundtruth_file = os.path.join(sequence_dir, "gt/gt.txt")
#     detections = np.load(detection_file) if detection_file is not None else None
#     groundtruth = np.loadtxt(groundtruth_file, delimiter=',') if os.path.exists(groundtruth_file) else None
#     image_size = cv2.imread(next(iter(image_filenames.values())), cv2.IMREAD_GRAYSCALE).shape if len(image_filenames) > 0 else None
#     min_frame_idx = min(image_filenames.keys()) if len(image_filenames) > 0 else int(detections[:, 0].min())
#     max_frame_idx = max(image_filenames.keys()) if len(image_filenames) > 0 else int(detections[:, 0].max())
#     feature_dim = detections.shape[1] - 10 if detections is not None else 0
#     seq_info = {
#         "sequence_name": os.path.basename(sequence_dir),
#         "image_filenames": image_filenames,
#         "detections": detections,
#         "groundtruth": groundtruth,
#         "image_size": image_size,
#         "min_frame_idx": min_frame_idx,
#         "max_frame_idx": max_frame_idx,
#         "feature_dim": feature_dim
#     }
#     return seq_info

# def select_bounding_boxes(frame):
#     boxes = []
#     current_box = []
#     def mouse_callback(event, x, y, flags, param):
#         if event == cv2.EVENT_LBUTTONDOWN:
#             current_box[:] = [x, y, x, y]
#         elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_LBUTTON:
#             current_box[2:] = [x, y]
#         elif event == cv2.EVENT_LBUTTONUP:
#             boxes.append((min(current_box[0], current_box[2]),
#                           min(current_box[1], current_box[3]),
#                           abs(current_box[2] - current_box[0]),
#                           abs(current_box[3] - current_box[1])))
#             current_box[:] = []
#     cv2.namedWindow("Image")
#     cv2.setMouseCallback("Image", mouse_callback)
#     while True:
#         img = frame.copy()
#         if current_box:
#             cv2.rectangle(img, (current_box[0], current_box[1]), (current_box[2], current_box[3]), (0, 255, 0), 2)
#         for box in boxes:
#             cv2.rectangle(img, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (0, 255, 0), 2)
#         cv2.imshow("Image", img)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#     cv2.destroyAllWindows()
#     return boxes

# def run(sequence_dir, detection_file, output_file, min_confidence, nms_max_overlap, min_detection_height, max_cosine_distance, nn_budget, display):
#     seq_info = gather_sequence_info(sequence_dir, detection_file)
#     metric = nn_matching.NearestNeighborDistanceMetric('cosine', max_cosine_distance, nn_budget)
#     tracker = Tracker(metric)
#     results = []

#     first_frame_path = seq_info["image_filenames"][min(seq_info["image_filenames"].keys())]
#     first_frame = cv2.imread(first_frame_path, cv2.IMREAD_COLOR)
#     initial_boxes = select_bounding_boxes(first_frame)

#     initial_detections = [Detection(box, 1.0, np.array([])) for box in initial_boxes]
#     tracker.update(initial_detections)

#     def frame_callback(vis, frame_idx):
#         if frame_idx == min(seq_info["image_filenames"].keys()):
#             return

#         image = cv2.imread(seq_info["image_filenames"][frame_idx], cv2.IMREAD_COLOR)
#         tracker.predict()
#         tracker.update([])  # Empty list as we don't want to add new detections

#         if display:
#             vis.set_image(image.copy())
#             vis.draw_trackers(tracker.tracks)

#         for track in tracker.tracks:
#             if not track.is_confirmed() or track.time_since_update > 1:
#                 continue
#             bbox = track.to_tlwh()
#             results.append([frame_idx, track.track_id, bbox[0], bbox[1], bbox[2], bbox[3]])
#             print("results")
#             print(results)

#     if display:
#         visualizer = visualization.Visualization(seq_info, update_ms=5)
#         visualizer.run(frame_callback)

#     with open(output_file, 'w') as f:
#         for row in results:
#             print('%d,%d,%.2f,%.2f,%.2f,%.2f,1,-1,-1,-1' % (
#                 row[0], row[1], row[2], row[3], row[4], row[5]), file=f)

# def bool_string(input_string):
#     if input_string not in {"True","False"}:
#         raise ValueError("Please Enter a valid True/False choice")
#     else:
#         return input_string == "True"

# def parse_args():
#     parser = argparse.ArgumentParser(description="Deep SORT")
#     parser.add_argument("--sequence_dir", help="Path to MOTChallenge sequence directory", required=True)
#     parser.add_argument("--detection_file", help="Path to custom detections.", required=True)
#     parser.add_argument("--output_file", help="Path to the tracking output file.", default="/tmp/hypotheses.txt")
#     parser.add_argument("--min_confidence", help="Detection confidence threshold.", default=0.8, type=float)
#     parser.add_argument("--min_detection_height", help="Threshold on the detection bounding box height.", default=0, type=int)
#     parser.add_argument("--nms_max_overlap", help="Non-maxima suppression threshold.", default=1.0, type=float)
#     parser.add_argument("--max_cosine_distance", help="Gating threshold for cosine distance metric.", type=float, default=0.2)
#     parser.add_argument("--nn_budget", help="Maximum size of the appearance descriptors gallery.", type=int, default=None)
#     parser.add_argument("--display", help="Show intermediate tracking results", default=True, type=bool_string)
#     return parser.parse_args()

# if __name__ == "__main__":
#     args = parse_args()
#     run(
#         args.sequence_dir, args.detection_file, args.output_file,
#         args.min_confidence, args.nms_max_overlap, args.min_detection_height,
#         args.max_cosine_distance, args.nn_budget, args.display)

# import argparse
# import os

# import cv2
# import numpy as np

# from application_util import preprocessing
# from application_util import visualization
# from deep_sort import nn_matching
# from deep_sort.detection import Detection
# from deep_sort.tracker import Tracker
# from opts import opt

# def gather_sequence_info(sequence_dir, detection_file):
#     image_dir = os.path.join(sequence_dir, "img1")
#     image_filenames = {int(os.path.splitext(f)[0]): os.path.join(image_dir, f) for f in os.listdir(image_dir) if os.path.splitext(f)[0].isdigit()}
#     groundtruth_file = os.path.join(sequence_dir, "gt/gt.txt")
#     detections = np.load(detection_file) if detection_file is not None else None
#     groundtruth = np.loadtxt(groundtruth_file, delimiter=',') if os.path.exists(groundtruth_file) else None
#     image_size = cv2.imread(next(iter(image_filenames.values())), cv2.IMREAD_GRAYSCALE).shape if len(image_filenames) > 0 else None
#     min_frame_idx = min(image_filenames.keys()) if len(image_filenames) > 0 else int(detections[:, 0].min())
#     max_frame_idx = max(image_filenames.keys()) if len(image_filenames) > 0 else int(detections[:, 0].max())
#     feature_dim = detections.shape[1] - 10 if detections is not None else 0
#     seq_info = {
#         "sequence_name": os.path.basename(sequence_dir),
#         "image_filenames": image_filenames,
#         "detections": detections,
#         "groundtruth": groundtruth,
#         "image_size": image_size,
#         "min_frame_idx": min_frame_idx,
#         "max_frame_idx": max_frame_idx,
#         "feature_dim": feature_dim
#     }
#     return seq_info

# def select_bounding_boxes(frame):
#     boxes = []
#     current_box = []
#     def mouse_callback(event, x, y, flags, param):
#         if event == cv2.EVENT_LBUTTONDOWN:
#             current_box[:] = [x, y, x, y]
#         elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_LBUTTON:
#             current_box[2:] = [x, y]
#         elif event == cv2.EVENT_LBUTTONUP:
#             boxes.append((min(current_box[0], current_box[2]),
#                           min(current_box[1], current_box[3]),
#                           abs(current_box[2] - current_box[0]),
#                           abs(current_box[3] - current_box[1])))
#             current_box[:] = []
#     cv2.namedWindow("Image")
#     cv2.setMouseCallback("Image", mouse_callback)
#     while True:
#         img = frame.copy()
#         if current_box:
#             cv2.rectangle(img, (current_box[0], current_box[1]), (current_box[2], current_box[3]), (0, 255, 0), 2)
#         for box in boxes:
#             cv2.rectangle(img, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (0, 255, 0), 2)
#         # Display instructions
#         cv2.putText(img, "Select boxes and press 'q' to continue", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
#         cv2.imshow("Image", img)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#     cv2.destroyAllWindows()
#     return boxes

# def run(sequence_dir, detection_file, output_file, min_confidence, nms_max_overlap, min_detection_height, max_cosine_distance, nn_budget, display):
#     seq_info = gather_sequence_info(sequence_dir, detection_file)
#     metric = nn_matching.NearestNeighborDistanceMetric('cosine', max_cosine_distance, nn_budget)
#     tracker = Tracker(metric)
#     results = []
#     first_frame_path = seq_info["image_filenames"][min(seq_info["image_filenames"].keys())]
#     first_frame = cv2.imread(first_frame_path, cv2.IMREAD_COLOR)
#     initial_boxes = select_bounding_boxes(first_frame)
    
#     # Correctly create Detection objects
#     initial_detections = [Detection(np.array([x, y, w, h]), 1.0, np.array([])) for x, y, w, h in initial_boxes]
#     tracker.update(initial_detections)

#     for frame_idx in range(seq_info['min_frame_idx'], seq_info['max_frame_idx'] + 1):
#         image = cv2.imread(seq_info["image_filenames"][frame_idx], cv2.IMREAD_COLOR)
#         tracker.predict()
#         current_detections = [Detection(np.array([x, y, w, h]), 1.0, np.array([])) for x, y, w, h in initial_boxes]
#         tracker.update(current_detections)

#         if display:
#             for track in tracker.tracks:
#                 if track.is_confirmed() and track.time_since_update <= 1:
#                     bbox = track.to_tlwh()
#                     cv2.rectangle(image, (int(bbox[0]), int(bbox[1])), (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])), (255, 255, 0), 2)
#                     cv2.putText(image, f"ID: {track.track_id}", (int(bbox[0]), int(bbox[1] - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
#             cv2.imshow('Tracking', image)
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break

#         for track in tracker.tracks:
#             if not track.is_confirmed() or track.time_since_update > 1:
#                 continue
#             bbox = track.to_tlwh()
#             results.append([frame_idx, track.track_id, bbox[0], bbox[1], bbox[2], bbox[3]])

#     with open(output_file, 'w') as f:
#         for row in results:
#             print('%d,%d,%.2f,%.2f,%.2f,%.2f,1,-1,-1,-1' % (
#                 row[0], row[1], row[2], row[3], row[4], row[5]), file=f)
#     if display:
#         cv2.destroyAllWindows()

# def bool_string(input_string):
#     if input_string not in {"True","False"}:
#         raise ValueError("Please Enter a valid True/False choice")
#     else:
#         return (input_string == "True")

# def parse_args():
#     parser = argparse.ArgumentParser(description="Deep SORT")
#     parser.add_argument("--sequence_dir", help="Path to MOTChallenge sequence directory", required=True)
#     parser.add_argument("--detection_file", help="Path to custom detections.", required=True)
#     parser.add_argument("--output_file", help="Path to the tracking output file.", default="/tmp/hypotheses.txt")
#     parser.add_argument("--min_confidence", help="Detection confidence threshold.", default=0.8, type=float)
#     parser.add_argument("--min_detection_height", help="Threshold on the detection bounding box height.", default=0, type=int)
#     parser.add_argument("--nms_max_overlap", help="Non-maxima suppression threshold.", default=1.0, type=float)
#     parser.add_argument("--max_cosine_distance", help="Gating threshold for cosine distance metric.", type=float, default=0.2)
#     parser.add_argument("--nn_budget", help="Maximum size of the appearance descriptors gallery.", type=int, default=None)
#     parser.add_argument("--display", help="Show intermediate tracking results", default=True, type=bool_string)
#     return parser.parse_args()

# if __name__ == "__main__":
#     args = parse_args()
#     run(
#         args.sequence_dir, args.detection_file, args.output_file,
#         args.min_confidence, args.nms_max_overlap, args.min_detection_height,
#         args.max_cosine_distance, args.nn_budget, args.display)
