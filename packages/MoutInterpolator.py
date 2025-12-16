import numpy as np
from scipy.interpolate import CubicSpline

def create_manual_output_interpolator(csv_path):
    """
    Reads a CSV with 'percentage' and 'temperature' columns and returns
    a function that interpolates manual output percentage for a given target temperature.
    
    Parameters:
        csv_path (str): Path to the CSV file.
    
    Returns:
        function: A function that takes a target temperature and returns the interpolated percentage.
    """
    # Load CSV assuming format: percentage,temperature (with or without header)
    data = np.genfromtxt(csv_path, delimiter=',', skip_header=0)  # Change to skip_header=0 if no header
    
    if data.ndim != 2 or data.shape[1] != 2:
        raise ValueError("CSV must contain exactly two columns: percentage and temperature.")
    
    percentages = data[:, 0]
    temperatures = data[:, 1]
    
    # Sort by temperature
    sort_idx = np.argsort(temperatures)
    temperatures = temperatures[sort_idx]
    percentages = percentages[sort_idx]
    
    # Create cubic spline: temperature → percentage
    spline = CubicSpline(temperatures, percentages, bc_type='natural')
    
    # Interpolation function with bounds check and rounding
    def get_manual_output(temp_target):
        if temp_target < temperatures[0] or temp_target > temperatures[-1]:
            raise ValueError(f"Target temperature {temp_target} K is out of range "
                             f"({temperatures[0]} K to {temperatures[-1]} K).")
        percent = spline(temp_target)
        return round(float(percent), 1)  # Ensure float and 1 decimal place

    return get_manual_output
if __name__=="__main__":
    get_output = create_manual_output_interpolator("manual_out_temps.csv")
    manual_output = get_output(5)
    print(f"Manual output for 50.0 K: {manual_output}%")