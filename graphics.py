"""
             Created on Tue Dec 14 11:28:34 2021

@author: Steven Adams, Neil Pohl, Chase Murray, and Samuel Geelhood

                Air Force Research Laboratory
"""
from bisect import bisect_left

import numpy as np

_MAX_RANGE = 200

def shape_lines(data_x, stick_wavelengths, stick_intensities, intensity_fraction, full_width_half_max):
    """
    Generates a simulated spectrum.
    :param data_x: A numpy array of wavelengths from an experimental dataset
    :param stick_wavelengths: A numpy array of wavelengths that corresponds to intensities
    :param stick_intensities: A numpy array of simulated spectral intensities
    :param intensity_fraction: A weighting factor used to mix gaussian functions with lorentzian functions
    :param full_width_half_max: Value of full-width-half-max for the simulated pseudo-voigts
    :return: A list of simulated relative intensities for each value of data_x
    """

    y = []
    for x in data_x:
        y.append(intensity_at_point(x, stick_wavelengths, stick_intensities, intensity_fraction, full_width_half_max))

    return np.array(y) / np.max(y)
    

def intensity_at_point(x, wavelengths, intensities, intensity_fraction, full_width_half_max):
    wavelength_max = x + _MAX_RANGE * full_width_half_max
    wavelength_min = x - _MAX_RANGE * full_width_half_max
    
    # Finds the starting point in the determined range
    start_index = bisect_left(wavelengths, wavelength_min)
    
    # Finds the ending point in the determined range
    end_index = bisect_left(wavelengths, wavelength_max)

    wavelengths = wavelengths[range(int(start_index), int(end_index))]
    intensities = intensities[range(int(start_index), int(end_index))]

    partial_intensities = intensities * pseudo_voigt(x, wavelengths, intensity_fraction, full_width_half_max)
    
    return np.sum(partial_intensities)

            
def pseudo_voigt(x, x_values, intensity_fraction, full_width_half_max):
    gau_sigma = full_width_half_max / (2 * np.sqrt(2 * np.log(2)))
    gaussian = (1 / (gau_sigma * np.sqrt(2 * np.pi))) * np.exp((-(x - x_values) ** 2) / (2 * gau_sigma ** 2))
    lorentzian = (1 / np.pi) * (0.5 * full_width_half_max) / ((x - x_values) ** 2 + (0.5 * full_width_half_max) ** 2)
    return intensity_fraction * gaussian + (1 - intensity_fraction) * lorentzian
