import torch
import torch.nn.functional as F
import time
import os
import math
import shutil
import os.path as osp
import matplotlib.pyplot as plt
import torchvision
from DPT.dpt.models import DPTDepthModel
from DPT.dpt.transforms import Resize, NormalizeImage, PrepareForNet
import matplotlib as mpl
import matplotlib.cm as cm
import argparse
import importlib
import numpy as np
from imageio import imread
import skimage
import skimage.transform
import cv2
class Inference(object):
    def __init__(self,
                 config):
        self.config = config
        
    def post_process_disparity(self,disp):
        disp = disp.cpu().detach().numpy()
        return disp   
    
    def inference(self):

        ## define network & load pre-trained model ##

        self.net = DPTDepthModel(
                    path=None,
                    backbone="vitb_rn50_384",
                    non_negative=True,
                    enable_attention_hooks=False,
                        )

        self.net.load_state_dict(torch.load(self.config.checkpoint_path))
        self.net.cuda()
        self.net.eval()

        ## load images to be evaluated
        image_list = os.listdir(self.config.data_path)
        eval_image = []
        for image_name in image_list:
            eval_image.append(os.path.join(self.config.data_path,image_name))
       
        
        for index,image_path in enumerate(eval_image):
            print(
               'Inference {}/{}'.format(index, len(
                        eval_image)),
                    end='\r')
             
            input_image = (imread(image_path).astype("float32")/255.0)
            
            input_image = skimage.transform.resize(input_image, [self.config.pred_height, self.config.pred_width])
            height, width, num_channels = input_image.shape
            
            inputs = input_image.astype(np.float32)
            inputs = torch.from_numpy(inputs).unsqueeze(0).float().permute(0,3,1,2).cuda()
            
            if not self.config.Input_Full:
                inputs = inputs[:,:,height//4: height - height//4,:]

            ## Forward pass  ##
            depth = self.net(inputs)

            ## Convert depth to disparity ## 
            max_value = torch.tensor([0.000005]).cuda()
            disp =1. / torch.max(depth.unsqueeze(0),max_value)

            disp_pp = self.post_process_disparity(disp).astype(np.float32).squeeze()

            eval_name = (image_path.split('/')[-1]).split('.')[0]
            np.save(os.path.join(self.config.output_path, eval_name+'.npy'), disp_pp)

            eval_name = (image_path.split('/')[-1]).split('.')[0]
            vmax = np.percentile(disp_pp, 95)
            normalizer = mpl.colors.Normalize(vmin=disp_pp.min(), vmax=vmax)
            mapper = cm.ScalarMappable(norm=normalizer, cmap='magma')
            disp_pp = (mapper.to_rgba(disp_pp)[:, :, :3] * 255).astype(np.uint8)

            save_name = eval_name +'_disp' '.png'        
    
            plt.imsave(os.path.join(self.config.output_path,save_name ), disp_pp, cmap='magma')



