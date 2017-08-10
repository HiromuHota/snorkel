import os
import numpy as np

from snorkel.parser import ImageCorpusExtractor, CocoPreprocessor
from snorkel.models import StableLabel
from snorkel.db_helpers import reload_annotator_labels

from snorkel.contrib.babble import Babbler
from snorkel.contrib.babble.models import BabbleModel


class BikeModel(BabbleModel):

    def parse(self, anns_path):
        self.anns_path = anns_path
        train_path = anns_path + 'train_anns.npy'
        val_path = anns_path + 'val_anns.npy'

        corpus_extractor = ImageCorpusExtractor(candidate_class=self.candidate_class)

        coco_preprocessor = CocoPreprocessor(train_path, source=0)
        corpus_extractor.apply(coco_preprocessor)

        coco_preprocessor = CocoPreprocessor(val_path, source=1)
        corpus_extractor.apply(coco_preprocessor, clear=False)


    def extract(self):
        print("Extraction was performed during parse stage.")
        for split in self.config['splits']:
            num_candidates = self.session.query(self.candidate_class).filter(
                self.candidate_class.split == split).count()
            print("Candidates [Split {}]: {}".format(split, num_candidates))

    def load_gold(self, anns_path=None, annotator_name='gold'):
        if anns_path:
            self.anns_path = anns_path
        labels_by_candidate = np.load(
            self.anns_path + 'labels_by_candidate.npy').tolist()

        for candidate_hash, label in labels_by_candidate.items():
            set_name, image_idx, bbox1_idx, bbox2_idx = candidate_hash.split(':')
            source = {'train': 0, 'val': 1}[set_name]
            stable_id_1 = "{}:{}::bbox:{}".format(source, image_idx, bbox1_idx)
            stable_id_2 = "{}:{}::bbox:{}".format(source, image_idx, bbox2_idx)
            context_stable_ids = "~~".join([stable_id_1, stable_id_2])
            query = self.session.query(StableLabel).filter(StableLabel.context_stable_ids == context_stable_ids)
            query = query.filter(StableLabel.annotator_name == annotator_name)
            label = 1 if label else -1
            if query.count() == 0:
                self.session.add(StableLabel(
                    context_stable_ids=context_stable_ids,
                    annotator_name=annotator_name,
                    value=label))

        self.session.commit()
        reload_annotator_labels(self.session, self.candidate_class, 
            annotator_name, split=1, filter_label_split=False)


    def babble(self, explanations, user_lists={}, **kwargs):
        babbler = Babbler(mode='image', candidate_class=self.candidate_class, explanations=explanations)
        super(BikeModel, self).babble(babbler, **kwargs)



def create_candidate(img_idx, p_idx, b_idx):
    """
    Create a BBox tuple with bbox p_idx and b_idx from image img_idx
    """
    anns_img = self.anns[img_idx]
    p_bbox = BBox(anns_img[p_idx],img_idx)
    b_bbox = BBox(anns_img[b_idx],img_idx)
    
    return (p_bbox, b_bbox)