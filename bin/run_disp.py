# #########################################################################
# Copyright (c) , UChicago Argonne, LLC. All rights reserved.             #
#                                                                         #
# See LICENSE file.                                                       #
# #########################################################################

"""
This user script processes reconstructed image for visualization.

After the script is executed the experiment directory will contain image.vts file for each reconstructed image in the given directory tree.
"""

__author__ = "Ross Harder"
__copyright__ = "Copyright (c), UChicago Argonne, LLC."
__docformat__ = 'restructuredtext en'
__all__ = ['save_CX',
           'save_vtk',
           'save_vtk_file',
           'get_conf_dict',
           'to_vtk',
           'main']

import reccdi.src_py.utilities.viz_util as vu
import reccdi.src_py.beamlines.aps_34id.viz as v
import reccdi.src_py.utilities.utils as ut
import reccdi.src_py.utilities.parse_ver as ver
import argparse
import sys
import os
import numpy as np
from multiprocessing import Pool, cpu_count


def save_CX(conf_dict, image, support, coh, save_dir):
    """
    Saves the image and support vts files.

    Parameters
    ----------
    conf_dict : dict
        dictionary containing configured parameters needed for visualization
    image : array
        image file in npy format
    support : array
        support file in npy format
    coh : array
        coherence file in npy format or None
    save_dir : str
        a directory where to save the processed vts file

    Returns
    -------
    nothing
    """
    params = v.DispalyParams(conf_dict)
    if support is not None:
        image, support = vu.center(image, support)
    if 'rampups' in conf_dict:
        image = vu.remove_ramp(image, ups=conf_dict['rampups'])
    viz = v.CXDViz(params)
    viz.set_geometry(image.shape)

    try:
        image_name = conf_dict['image_name']
    except:
        image_name = 'image'
    arrays = {"imAmp" : abs(image), "imPh" : np.angle(image)}
    viz.add_ds_arrays(arrays)
    # viz.add_ds_array(abs(image), "imAmp")
    # viz.add_ds_array(np.angle(image), "imPh")
    image_file = os.path.join(save_dir, image_name)
    viz.write_directspace(image_file)
    viz.clear_direct_arrays()

    if support is not None:
        arrays = {"support" : support}
        viz.add_ds_arrays(arrays)
        # viz.add_ds_array(support, "support")
        support_file = os.path.join(save_dir, 'support')
        viz.write_directspace(support_file)
        viz.clear_direct_arrays()

    if coh is not None:
        coh = ut.get_zero_padded_centered(coh, image.shape)
        coh = np.fft.fftshift(np.fft.fftn(np.fft.fftshift(coh)))
        coh_file = os.path.join(save_dir, 'coherence')
        arrays = {"cohAmp" : np.abs(coh), "cohPh" : np.angle(coh)}
        viz.add_ds_arrays(arrays)
        # viz.add_ds_array(np.abs(coh), 'cohAmp')
        # viz.add_ds_array(np.angle(coh), 'cohPh')
        viz.write_directspace(coh_file)
        viz.clear_direct_arrays()


def save_vtk(res_dir_conf):
    """
    Loads arrays from files in results directory. If reciprocal array exists, it will save reciprocal info in tif format. It calls the save_CX function with the relevant parameters.

    Parameters
    ----------
    res_dir_conf : tuple
        tuple of two elements:
        res_dir - directory where the results of reconstruction are saved
        conf_dict - dictionary containing configuration parameters

    Returns
    -------
    nothing
    """
    (res_dir, conf_dict) = res_dir_conf
    try:
        imagefile = os.path.join(res_dir, 'image.npy')
        image = np.load(imagefile)
    except:
        print('cannot load "image.npy" file')
        return

    try:
        supportfile = os.path.join(res_dir, 'support.npy')
        support = np.load(supportfile)
    except:
        print('support file is missing in ' + res_dir + ' directory')
        return

    cohfile = os.path.join(res_dir, 'coherence.npy')
    if os.path.isfile(cohfile):
        coh = np.load(cohfile)
        save_CX(conf_dict, image, support, coh, res_dir)
    else:
        save_CX(conf_dict, image, support, None, res_dir)


def save_vtk_file(image_file, conf_dict):
    """
    Loads array from given image file. Determines the vts file name and calls savw_CX function to process this  file. The vts file will have the same name as image file, with different extension and will be saved in the same directory.

    Parameters
    ----------
    image_file : str
        name of file in npy format containing reconstructrd image
    conf_dir : str
        dictionary containing configuration parameters

    Returns
    -------
    nothing
    """
    image_file_name = image_file.split('/')[-1]
    image_file_name = image_file_name[0:-4]
    conf_dict['image_name'] = image_file_name
    image = np.load(image_file)
    res_dir = os.path.dirname(image_file)
    save_CX(conf_dict, image, None, None, res_dir)


def get_conf_dict(experiment_dir):
    """
    Reads configuration files and creates dictionary with parameters that are needed for visualization.

    Parameters
    ----------
    experiment_dir : str
        directory where the experiment files are located

    Returns
    -------
    conf_dict : dict
        a dictionary containing configuration parameters
    """
    if not os.path.isdir(experiment_dir):
        print("Please provide a valid experiment directory")
        return None
    conf_dir = os.path.join(experiment_dir, 'conf')
    conf = os.path.join(conf_dir, 'config_disp')
    # verify configuration file
    if not ver.ver_config_disp(conf):
        print ('incorrect configuration file ' + conf +', cannot parse')
        return None

    # parse the conf once here and save it in dictionary, it will apply to all images in the directory tree
    conf_dict = {}
    try:
        conf_map = ut.read_config(conf)
        items = conf_map.items()
        for item in items:
            key = item[0]
            val = item[1]
            conf_dict[key] = val
    except:
        return None

    # get specfile and last_scan from the config file and add it to conf_dict
    main_conf = os.path.join(conf_dir, 'config')
    specfile = None
    last_scan = None
    if os.path.isfile(main_conf):
        try:
            config_map = ut.read_config(main_conf)
        except:
            print ("info: scan not determined, can't read " + conf + " configuration file")
        try:
            specfile=config_map.specfile
            conf_dict['specfile'] = specfile
            scan = config_map.scan
            last_scan = scan.split('-')[-1]
            conf_dict['last_scan'] = int(last_scan)
        except:
            print("specfile not in main config")

    # get binning from the config_data file and add it to conf_dict
    binning = None
    data_conf = os.path.join(conf_dir, 'config_data')
    if os.path.isfile(data_conf):
        try:
            conf_map = ut.read_config(data_conf)
            conf_dict['binning'] = conf_map.binning
        except:
            pass
    return conf_dict


def to_vtk(experiment_dir, image_file=None):
    """
    If the image_file parameter is defined, the file is processed and vts file saved. Otherwise this function determines root directory with results that should be processed for visualization. Multiple images will be processed concurrently.

    Parameters
    ----------
    conf_dir : str
        directory where the file will be saved

    Returns
    -------
    nothing
    """
    conf_dict = get_conf_dict(experiment_dir)
    if conf_dict is None:
        return
    if image_file is not None:
        save_vtk_file(image_file, conf_dict)
    else:
        try:
            results_dir = conf_dict['results_dir']
        except  Exception as ex:
            print(str(ex))
            results_dir = experiment_dir
        # find directories with image.npy file
        dirs = []
        for (dirpath, dirnames, filenames) in os.walk(results_dir):
            for file in filenames:
                if file.endswith('image.npy'):
                    dirs.append((dirpath, conf_dict))
        if len(dirs) == 1:
            save_vtk(dirs[0])
        elif len(dirs) >1:
            no_proc = min(cpu_count(), len(dirs))
            with Pool(processes = no_proc) as pool:
               pool.map_async(save_vtk, dirs)
               pool.close()
               pool.join()
        print ('done with processing display')


def main(arg):
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_dir", help="experiment directory")
    parser.add_argument("--image_file", help="a file in .npy format to be processed for visualization")
    args = parser.parse_args()
    experiment_dir = args.experiment_dir
    if args.image_file:
        to_vtk(experiment_dir, args.image_file)
    else:
        to_vtk(experiment_dir)


if __name__ == "__main__":
    main(sys.argv[1:])

# python run_disp.py experiment_dir
