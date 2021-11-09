import torch
torch.autograd.set_detect_anomaly(True)
import torch.nn as nn
import torchvision
from torchvision import models
torch.cuda.set_device(2)
import sys

class LSTMController(nn.Module):
    def __init__(self, hidden_dim, cnn_channels, avg_pool, layers):
        super(LSTMController, self).__init__()
        resnet_cutoff = -1 if avg_pool else -2
        resnet_out_channels = 512
        self._hidden_dim = hidden_dim
        self._layers = layers
        self._cnn_out = cnn_channels * 7 * 7

        self.init_hidden()

        self._resnet = self.init_resnet(resnet_cutoff)
        self._conv = nn.Conv2d(resnet_out_channels, cnn_channels, 1)
        self._flatten = nn.Flatten()
        self._lstm = nn.LSTM(self._cnn_out + 3, hidden_dim, layers)
        self._fc2 = nn.Linear(hidden_dim, 6)
        self._fc3 = nn.Linear(hidden_dim, 1)

        self._tanh = nn.Tanh()
        self._sigmoid = nn.Sigmoid()

    def init_hidden(self):
        self._hidden = (torch.zeros(self._layers, 1, self._hidden_dim).cuda(),
                        torch.zeros(self._layers, 1, self._hidden_dim).cuda())

    def init_resnet(self, cutoff):
        res18_model = models.resnet18(pretrained=True)
        res18_model = nn.Sequential(*list(res18_model.children())[:cutoff]).cuda()

        return res18_model

    def forward(self, X_img, X_coords):
        with torch.no_grad():
            X = self._resnet(X_img.float()).detach()
        torch.cuda.empty_cache()

        X = self._sigmoid(self._conv(X))
        X = self._flatten(X)
        X = torch.cat((X, X_coords), 1)

        lstm_out, self._hidden = self._lstm(X.view(len(X), 1, -1), self._hidden)
        lstm_out = lstm_out.view(len(X), -1)

        out_vel = self._tanh(self._fc2(lstm_out))
        out_claw = self._sigmoid(self._fc3(lstm_out))
        
        return out_vel, out_claw

if __name__ == "__main__" :
    print(models.__file__)
    lstm = LSTMController(500,500).cuda()
    lstm(torch.randn((100,3,244,244)).cuda())

