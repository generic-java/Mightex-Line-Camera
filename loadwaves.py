import csv
import re
from urllib import request

import numpy as np
from bs4 import BeautifulSoup
from matplotlib import pyplot as plt

from graphics import shape_lines

_invalid_nist = None

with open("./res/files/invalid_nist.txt") as nist_file:
    # noinspection PyRedeclaration
    _invalid_nist = nist_file.read()

def fetch_waves(upper, lower, element, save_path):
    """
    :param save_path: The path to save the data to
    :param upper: Upper wavelength
    :param lower: Lower wavelength
    :param element: The element in question (e.g. "H" for hydrogen)
    Author: Neil Pohl and Samuel Geelhood
    """

    url = f"https://physics.nist.gov/cgi-bin/ASD/lines1.pl?spectra={element}&limits_type=0&low_w={lower}&upp_w={upper}&unit=1&de=0&format=3&line_out=0&remove_js=on&en_unit=0&output=0&bibrefs=1&page_size=15&show_obs_wl=1&show_calc_wl=1&unc_out=1&order_out=0&max_low_enrg=&show_av=2&max_upp_enrg=&tsb_value=0&min_str=&A_out=0&intens_out=on&max_str=&allowed_out=1&forbid_out=1&min_accur=&min_intens=&conf_out=on&term_out=on&enrg_out=on&J_out=on&submit=Retrieve+Data"

    print(url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "http://google.com"
    }

    req = request.Request(url, headers=headers)

    try:
        with request.urlopen(req) as response:
            html_bytes = response.read()
            html = html_bytes.decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")
            data = soup.get_text()
            with open(save_path, "w") as file:
                file.write(data)

    except Exception as e:
        print("Error:", e)

def read_nist_data(fpath, wavelength_min, wavelength_max, intensity_fraction, full_width_half_max):
    wavelengths = []
    intensities = []

    obs_wl_air_id = "obs_wl_air(nm)"
    obs_wl_vac_id = "obs_wl_vac(nm)"

    on_header = True
    with open(fpath) as file:
        if _invalid_nist and file.read() == _invalid_nist:
            raise AttributeError
        file.seek(0) # reset current read position to 0 bytes from start of file
        reader = csv.reader(file, delimiter = "\t")
        for line in reader:
            if on_header:
                obs_wl_air_index = line.index(obs_wl_air_id) if obs_wl_air_id in line else None
                obs_wl_vac_index = line.index(obs_wl_vac_id) if obs_wl_vac_id in line else None
                intensity_index = line.index("intens")
                on_header = False
            else:
                pattern = r"(-?[0-9]*\.?[0-9]*)"
                intensity_match = re.match(pattern, line[intensity_index]).group(1)

                if intensity_match:
                    if obs_wl_air_index is not None:
                        obs_wl_air_match = re.match(pattern, line[obs_wl_air_index]).group(1)
                        if obs_wl_air_match:
                            wavelengths.append(float(obs_wl_air_match))
                            intensities.append(float(intensity_match))

                    elif obs_wl_vac_index is not None:
                        obs_wl_air_match = re.match(pattern, line[obs_wl_vac_index]).group(1)
                        if obs_wl_air_match:
                            wavelengths.append(float(obs_wl_air_match))
                            intensities.append(float(intensity_match))

    wavelengths = np.array(wavelengths)
    intensities = np.array(intensities)
    generated_wavelengths = np.linspace(wavelength_min, wavelength_max,5000)
    generated_intensities = shape_lines(generated_wavelengths, wavelengths, intensities, intensity_fraction, full_width_half_max)
    return generated_wavelengths, generated_intensities

def load_waves(fpath: str, row_start=0, wavelength_col=0, intensity_col=0, delimiter: str=","):
    wavelengths = []
    intensities = []
    with open(fpath, "r") as file:
        reader = csv.reader(file, delimiter=delimiter)
        line_num = 0
        for line in reader:
            try:
                if line_num >= row_start:
                    wavelengths.append(float(line[wavelength_col]))
                    intensities.append(float(line[intensity_col]))
            except ValueError:
                pass
            finally:
                line_num += 1

    return np.array(wavelengths), np.array(intensities)

def save_waves(fpath, first_column, second_column, delimiter=","):
    with open(fpath, "w") as file:
        data = np.transpose(np.column_stack((first_column, second_column)))
        text = ""
        for row in data:
            text += str(row[0]) + delimiter + str(row[1]) + "\n"
        file.write(text)

def main():
    wavelengths, intensities = read_nist_data(r"C:\Users\power\Downloads\waves.txt", 400, 700, 0.1, 2)
    figure, axes = plt.subplots()
    axes.plot(wavelengths, intensities)
    figure.canvas.manager.set_window_title("Hydrogen Lines")
    plt.show()

if __name__ == "__main__":
    main()


