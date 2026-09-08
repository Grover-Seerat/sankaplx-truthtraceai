"""Minimal inference implementation of the public NPR detector architecture."""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F

class Bottleneck(nn.Module):
    expansion=4
    def __init__(self,inplanes,planes,stride=1,downsample=None):
        super().__init__()
        self.conv1=nn.Conv2d(inplanes,planes,1,bias=False); self.bn1=nn.BatchNorm2d(planes)
        self.conv2=nn.Conv2d(planes,planes,3,stride=stride,padding=1,bias=False); self.bn2=nn.BatchNorm2d(planes)
        self.conv3=nn.Conv2d(planes,planes*4,1,bias=False); self.bn3=nn.BatchNorm2d(planes*4)
        self.relu=nn.ReLU(inplace=True); self.downsample=downsample
    def forward(self,x):
        identity=x
        out=self.relu(self.bn1(self.conv1(x))); out=self.relu(self.bn2(self.conv2(out))); out=self.bn3(self.conv3(out))
        if self.downsample is not None: identity=self.downsample(x)
        return self.relu(out+identity)

class NPRResNet(nn.Module):
    """Official NPR ResNet-50 path: layer1/2 + 512-d classifier."""
    def __init__(self,num_classes=1):
        super().__init__(); self.inplanes=64
        self.conv1=nn.Conv2d(3,64,3,stride=2,padding=1,bias=False); self.bn1=nn.BatchNorm2d(64); self.relu=nn.ReLU(inplace=True); self.maxpool=nn.MaxPool2d(3,stride=2,padding=1)
        self.layer1=self._make_layer(64,3); self.layer2=self._make_layer(128,4,stride=2); self.avgpool=nn.AdaptiveAvgPool2d((1,1)); self.fc1=nn.Linear(512,num_classes)
    def _make_layer(self,planes,blocks,stride=1):
        downsample=None
        if stride!=1 or self.inplanes!=planes*Bottleneck.expansion:
            downsample=nn.Sequential(nn.Conv2d(self.inplanes,planes*Bottleneck.expansion,1,stride=stride,bias=False),nn.BatchNorm2d(planes*Bottleneck.expansion))
        layers=[Bottleneck(self.inplanes,planes,stride,downsample)]; self.inplanes=planes*Bottleneck.expansion
        for _ in range(1,blocks): layers.append(Bottleneck(self.inplanes,planes))
        return nn.Sequential(*layers)
    @staticmethod
    def _interpolate(img,factor):
        x=F.interpolate(img,scale_factor=factor,mode='nearest',recompute_scale_factor=True)
        return F.interpolate(x,scale_factor=1/factor,mode='nearest',recompute_scale_factor=True)
    def forward(self,x):
        npr=x-self._interpolate(x,.5); x=self.relu(self.bn1(self.conv1(npr*2/3))); x=self.maxpool(x); x=self.layer1(x); x=self.layer2(x); x=self.avgpool(x).flatten(1); return self.fc1(x)
