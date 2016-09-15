# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import numpy as np

def convert2ras(data):
    """Convert dataset from original space into RAS space.
    Original space:
        axis i: A->P
        axis j: I->S
        axis k: R->L
    """
    # reverse axis i (A-P to P-A)
    ndata = data[::-1, :, :]
    # reverse axis k (R-L to L-R)
    #ndata = ndata[:, :, ::-1]
    # convert matrix into RAS space
    ndata = np.rollaxis(ndata, 2)
    return ndata

def idx2coord(vec_idx):
    """Convert row index in response data matrix into 3D coordinate in
    (original) ROI volume.
    """
    data_size = (18, 64, 64)
    coord_z = vec_idx % data_size[2]
    coord_x = vec_idx / (data_size[1]*data_size[2])
    coord_y = (vec_idx % (data_size[1]*data_size[2])) / data_size[2]
    return (coord_x, coord_y, coord_z)

