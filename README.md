Codes are available at https://github.com/dyhBUPT/StrongSORT
and https://github.com/open-mmlab/mmtracking
Data&Model Preparation

Download MOT17 & MOT20 from the official website.

path_to_dataset/MOTChallenge
├── MOT17
	│   ├── test
	│   └── train
└── MOT20
    ├── test
    └── train

Download our prepared data in Google disk (or baidu disk with code "sort")

path_to_dataspace
├── AFLink_epoch20.pth  # checkpoints for AFLink model
├── MOT17_ECC_test.json  # CMC model
├── MOT17_ECC_val.json  # CMC model
├── MOT17_test_YOLOX+BoT  # detections + features
├── MOT17_test_YOLOX+simpleCNN  # detections + features
├── MOT17_trainval_GT_for_AFLink  # GT to train and eval AFLink model
├── MOT17_val_GT_for_TrackEval  # GT to eval the tracking results.
├── MOT17_val_YOLOX+BoT  # detections + features
├── MOT17_val_YOLOX+simpleCNN  # detections + features
├── MOT20_ECC_test.json  # CMC model
├── MOT20_test_YOLOX+BoT  # detections + features
├── MOT20_test_YOLOX+simpleCNN  # detections + features

    Set the paths of your dataset and other files in "opts.py", i.e., root_dataset, path_AFLink, dir_save, dir_dets, path_ECC.

Note: If you want to generate ECC results, detections and features by yourself, please refer to the Auxiliary tutorial.
Requirements

    pytorch
    opencv
    scipy
    sklearn

For example, we have tested the following commands to create an environment for StrongSORT:

conda create -n strongsort python=3.8 -y
conda activate strongsort
pip3 install torch torchvision torchaudio
pip install opencv-python
pip install scipy
pip install scikit-learn==0.19.2

Tracking

Run DeepSORT on MOT17-val

python strong_sort.py MOT17 val

Run StrongSORT on MOT17-val

python strong_sort.py MOT17 val --BoT --ECC --NSA --EMA --MC --woC

Run StrongSORT++ on MOT17-val

python strong_sort.py MOT17 val --BoT --ECC --NSA --EMA --MC --woC --AFLink --GSI

Run StrongSORT++ on MOT17-test

python strong_sort.py MOT17 test --BoT --ECC --NSA --EMA --MC --woC --AFLink --GSI

Run StrongSORT++ on MOT20-test

python strong_sort.py MOT20 test --BoT --ECC --NSA --EMA --MC --woC --AFLink --GSI

