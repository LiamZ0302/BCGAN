from __future__ import print_function
import argparse
import math
import os
import random
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim as optim
import torch.utils.data
import torchvision.datasets as dset
import torchvision.transforms as transforms
import torchvision.utils as vutils
import numpy
from model_GAN import Generator
from model_GAN import Discriminator
from model_ae import *
# from simple_ae import Encoder

nz = 64 # size of latent variable
ngf = 64 
ndf = 64 
np = 4

lr_D = 1e-3
lr_G = 2e-3
batchSize = 64
workers = 2 # 'number of data loading workers'
nepochs = 30
beta1 = 0.5 # 'beta1 for adam. default=0.5'
weight_decay_coeff = 5e-4 # weight decay coefficient for training netE.
default_device = 'cuda:0'

parser = argparse.ArgumentParser()
parser.add_argument('--outf', default='./trained_model', help='folder to output model checkpoints')
parser.add_argument('--outp', default='./fake-imgs', help='folder to output images')
parser.add_argument('--manualSeed', type=int, help='manual random seed')
opt = parser.parse_args()
print(opt)

try:
    os.makedirs(opt.outf)
except OSError:
    pass

if opt.manualSeed is None:
    opt.manualSeed = random.randint(1, 10000)
print("Random Seed: ", opt.manualSeed)
random.seed(opt.manualSeed)
torch.manual_seed(opt.manualSeed)

cudnn.benchmark = True

class SyntheticData(torch.utils.data.Dataset):
    def __init__(self, num_of_data=10000):
        super(SyntheticData, self).__init__()
        self.data = torch.empty(num_of_data, 128)
        mu1 = torch.zeros(128)
        mu1[0] = 1
        mu2 = torch.zeros(128)
        mu2[0] = 5
        for i in range(num_of_data):
            tmp = torch.rand(1).item()
            if tmp < 0.75:
                self.data[i, :] = torch.normal(mean=mu1)
            else:
                self.data[i, :] = torch.normal(mean=mu2)
        return

    def __getitem__(self, i):
        return self.data[i, :]

    def __len__(self):
        return len(self.data)
    
dataset = SyntheticData()

assert dataset
dataloader = torch.utils.data.DataLoader(dataset, batch_size=batchSize,
                                        shuffle=True, num_workers=int(workers))


device = torch.device(default_device)


netG = Generator(nz, ngf).to(device)
print(netG)

netD = Discriminator(ndf, np).to(device)
print(netD)

# encoder = torch.load('./sim_encoder.pth')
# encoder.eval()


criterion_BCE = nn.BCELoss()


fixed_noise = torch.randn(batchSize, nz, device=device)

# setup optimizer
optimizerD = optim.Adam(netD.parameters(), lr=lr_D, betas=(beta1, 0.999))
optimizerG = optim.Adam(netG.parameters(), lr=lr_G, betas=(beta1, 0.999))


for epoch in range(nepochs):
    for i, data in enumerate(dataloader, 0):
        ############################
        # (1) Update D network: maximize log(D(x)) + log(1 - D(G(z)))
        ###########################
        # train with real
        # netD.zero_grad()
        real = data.to(device)
        batch_size = real.size(0)
        noise = torch.randn(batch_size, nz, device=device)
        
        label_real = torch.full((batch_size, 1), 1, device=device, dtype=torch.float32)
        output = netD(real)[0] # normalized
        errD = criterion_BCE(output, label_real)
        D_x = output.mean().item()
        label_fake = torch.full((batch_size, 1), 0, device=device, dtype=torch.float32)
        output = netD(netG(noise))[0]
        errD += criterion_BCE(output, label_fake)
        
        D_Gz = output.mean().item()
        errG = criterion_BCE(output, label_real)
        
        optimizerD.zero_grad()
        errD.backward(retain_graph=True)
        optimizerD.step()

        ############################
        # (2) Update G network: maximize log(D(G(z)))
        ###########################
        optimizerG.zero_grad()
        errG.backward()
        optimizerG.step()

        ############################
        # (3) Update E network: minimize reconstruction error
        ###########################
        
        if i % 1000 == 0:
            print('[%d/%d][%d/%d] Loss_D: %.4f Loss_G: %.4f D(x):%.4f D(G(z)):%.4f'
            % (epoch, nepochs, i, len(dataloader), errD.item(), errG.item(), D_x, D_Gz))
    

torch.save(netG.state_dict(), '%s/final_netG.pth' % (opt.outf))
torch.save(netD.state_dict(), '%s/final_netD.pth' % (opt.outf))