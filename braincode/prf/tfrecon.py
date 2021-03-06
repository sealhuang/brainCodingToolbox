# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import numpy as np
import tables
import tensorflow as tf
import matplotlib.pyplot as plt

from braincode.util import configParser


def reconstructor(gabor_bank, vxl_coding_paras, y):
    """Stimuli reconstructor based on Activation Maximization"""
    # var for input stimuli
    img = tf.Variable(tf.zeros([1, 500, 500, 1]))
    # config for the gabor filters
    gabor_real = np.expand_dims(gabor_bank['gabor_real'], 2)
    gabor_imag = np.expand_dims(gabor_bank['gabor_imag'], 2)
    real_conv = tf.nn.conv2d(img, gabor_real, strides=[1, 1, 1, 1],
                             padding='SAME')
    imag_conv = tf.nn.conv2d(img, gabor_imag, strides=[1, 1, 1, 1],
                             padding='SAME')
    gabor_energy = tf.sqrt(tf.square(real_conv) + tf.square(imag_conv))
    vxl_wts = vxl_coding_paras['wt']
    vxl_bias = vxl_coding_paras['bias']
    vxl_conv = tf.nn.conv2d(gabor_energy, vxl_wts, strides=[1, 1, 1, 1],
                            padding='VALID')
    vxl_conv = tf.reshape(vxl_conv, [-1])
    vxl_pred = vxl_conv - vxl_bias
    vxl_real = tf.placeholder(tf.float32,
                shape=(None, vxl_coding_paras['bias'].shape[0]))
    error = tf.reduce_mean(tf.square(vxl_pred - vxl_real))
    opt = tf.train.AdamOptimizer(1e-3, beta1=0.5)
    solver =  opt.minimize(error, var_list=img)
 
    # training
    config = tf.ConfigProto()
    config.gpu_options.per_process_gpu_memory_fraction = 0.9
    sess = tf.Session(config=config)
    sess.run(tf.global_variables_initializer())     
    _, error_curr, reconstructed_img = sess.run([solver, error, img],
                                                feed_dict={vxl_real: y[:, 2]})
    return reconstructed_img

def model_test(input_imgs, gabor_bank, vxl_coding_paras):
    """Stimuli reconstructor based on Activation Maximization"""
    # var for input stimuli
    img = tf.placeholder("float", shape=[None, 500, 500, 1])
    # config for the gabor filters
    gabor_real = np.expand_dims(gabor_bank['gabor_real'], 2)
    gabor_imag = np.expand_dims(gabor_bank['gabor_imag'], 2)
    real_conv = tf.nn.conv2d(img, gabor_real, strides=[1, 1, 1, 1],
                             padding='SAME')
    imag_conv = tf.nn.conv2d(img, gabor_imag, strides=[1, 1, 1, 1],
                             padding='SAME')
    gabor_energy = tf.sqrt(tf.square(real_conv) + tf.square(imag_conv))
    #gabor_pool = tf.nn.avg_pool(gabor_energy, ksize=[1, 2, 2, 1],
    #                            strides=[1, 2, 2, 1], padding='SAME')
    #gabor_pool = tf.image.resize_images(gabor_energy, size=[250, 250])
    vxl_wts = vxl_coding_paras['wt']
    vxl_bias = vxl_coding_paras['bias']
    vxl_conv = tf.nn.conv2d(gabor_energy, vxl_wts, strides=[1, 1, 1, 1],
                            padding='VALID')
    vxl_conv = tf.reshape(vxl_conv, [-1])
    vxl_out = vxl_conv - vxl_bias
    with tf.Session() as sess:
        sess.run(tf.initialize_all_variables())
        for i in range(input_imgs.shape[2]):
            x = input_imgs[..., i].T
            x = np.expand_dims(x, 0)
            x = np.expand_dims(x, 3)
            resp = sess.run(vxl_out, feed_dict={img: x})
            print resp

if __name__ == '__main__':
    """Main function"""
    # config parser
    cf = configParser.Config('config')
    # database directory config
    db_dir = os.path.join(cf.get('database', 'path'), 'vim1')
    # directory config for analysis
    root_dir = cf.get('base', 'path')
    feat_dir = os.path.join(root_dir, 'sfeatures', 'vim1')
    res_dir = os.path.join(root_dir, 'subjects')

    #-- general config
    subj_id = 1
    roi = 'v1'
    # directory config
    subj_dir = os.path.join(res_dir, 'vim1_S%s'%(subj_id))
    prf_dir = os.path.join(subj_dir, 'prf')

    # parameter preparation
    gabor_bank_file = os.path.join(feat_dir, 'gabor_kernels.npz')
    gabor_bank = np.load(gabor_bank_file)
    vxl_coding_paras_file = os.path.join(prf_dir, roi, 'tfrecon',
                                         'vxl_coding_wts_1.npz')
    vxl_coding_paras = np.load(vxl_coding_paras_file)

    #-- test encoding model
    #img_file = os.path.join(root_dir, 'example_imgs.npy')
    #imgs = np.load(img_file)
    #model_test(imgs, gabor_bank, vxl_coding_paras)

    #-- stimuli reconstruction
    resp_file = os.path.join(db_dir, 'EstimatedResponses.mat')
    resp_mat = tables.open_file(resp_file)
    # create mask
    # train data shape: (1750, ~25000)
    train_ts = resp_mat.get_node('/dataTrnS%s'%(subj_id))[:]
    train_ts = train_ts.T
    # get non-NaN voxel index
    fmri_s = train_ts.sum(axis=1)
    non_nan_idx = np.nonzero(np.logical_not(np.isnan(fmri_s)))[0]
    rois = resp_mat.get_node('/roiS%s'%(subj_id))[:]
    rois = rois[0]
    roi_idx = {'v1': 1, 'v2': 2, 'v3': 3, 'v3a': 4,
               'v3b': 5, 'v4': 6, 'LO': 7}
    vxl_idx = np.nonzero(rois==roi_idx[roi])[0]
    vxl_idx = np.intersect1d(vxl_idx, non_nan_idx)
    # load fmri response: data shape (#voxel, 1750/120)
    train_ts = np.nan_to_num(train_ts[vxl_idx])
    m = np.mean(train_ts, axis=1, keepdims=True)
    s = np.std(train_ts, axis=1, keepdims=True)
    train_ts = (train_ts - m) / (s + 1e-5)
    #val_ts = tf.get_node('/dataValS%s'%(subj_id))[:]
    #val_ts = val_ts.T
    #val_ts = np.nan_to_num(val_ts[vxl_idx])
    resp_mat.close()
    y_ = train_ts[vxl_coding_paras['vxl_idx']]
    # shape: (#voxel, 1750)
    print y_.shape
    recon_img = reconstructor(gabor_bank, vxl_coding_paras, y_)
 
    # show image
    plt.imshow(recon_img.reshape(500, 500))

