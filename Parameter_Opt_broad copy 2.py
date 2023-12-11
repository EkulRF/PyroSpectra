# Import necessary libraries and modules
import os
import numpy as np
import random
from Toolbox.Toolbox_Processing import *
from Toolbox.Toolbox_Reading import *
from Toolbox.Toolbox_Inversion import *
from Toolbox.Toolbox_Display import *

# Define the path to the spectra data
#path = "/home/luke/lukeflamingradis/EmFit_private/spectra/test_series"
base_path = "/home/luke/data/MATRIX_data/"
dataset = "Peat6"

os.makedirs('/home/luke/data/Model/results_param/'+dataset+'/', exist_ok=True)

P, T = getPT(dataset)

# Load chemical compound information from a pickle file
Compounds = getCompounds('/home/luke/lukeflamingradis/EmFit_private/Compounds.pickle')

# List of compounds to be removed from the Compounds dictionary
remove = ['SiH', 'CaF', 'SiS', 'BeH', 'HF', 'NH', 'SiH2', 'AlF', 'SH', 'CH', 'AlH', 'TiH', 'CaH', 'LiF', 'MgH', 'ClO', 'CH3Br', 'H2S']

# Remove specified compounds from the Compounds dictionary
for r in remove:
    Compounds.pop(r)

regularisation_constant = 10**(-3)

ref_spec, obs_spec, full_ref_spec, Compounds = generateData(Compounds, base_path + dataset, 0, 273, 1.01325, dataset)

ref_spec, Compounds, Lasso_Evaluation, full_ref_spec = lasso_inversion(ref_spec, full_ref_spec, obs_spec, Compounds)

x_sol, sigma, C = temporally_regularised_inversion(ref_spec, obs_spec, regularisation_constant, dataset, list(Compounds.keys()))

(Ns, Nl), Nt = ref_spec.shape, obs_spec.shape[0]

from scipy.optimize import minimize

def generateSingleRef(comp, W_obs, T, P):

    output = []
    norm_constant = 1 / (np.sqrt(2 * np.pi) * sigma)

    bank = comp['Source']
    tmp = np.zeros_like(W_obs)

    for i in range(len(comp['bounds'])):
        bound = comp['bounds'][i]
        try:
            s = calc_spectrum(
                bound[0], bound[1],  # cm-1
                molecule=c,
                isotope='1',
                pressure=P,  # bar
                Tgas=T,  # K
                mole_fraction=10**(-6),
                path_length=500,  # cm
                warnings={'AccuracyError':'ignore'},
            )
        except:
            print("BAD", c)
            continue

        s.apply_slit(0.241, 'cm-1', shape="gaussian")  # Simulate an experimental slit
        w, A = s.get('absorbance', wunit='cm-1')

        iloc, jloc = np.argmin(np.abs(w.min() - W_obs)), np.argmin(np.abs(w.max() - W_obs))
        s.resample(W_obs[iloc:jloc], energy_threshold=2)

        w, A = s.get('absorbance', wunit='cm-1')

        tmp[iloc:jloc] = A

    ref_mat = np.array(tmp)

    return ref_mat

def cost_function(params, observed_spectra, theoretical_spectra):
    T_values = params[:len(params)//2]
    P_values = params[len(params)//2:]

    # Calculate the sum of squared differences between observed and theoretical spectra
    cost = np.sum((observed_spectra - theoretical_spectra)**2)
    return cost

wv_obs = np.load('/home/luke/data/Model/results/'+ dataset + '/W_full.npy')
T_guess = np.linspace(273, 473, 100)
P_guess = np.linspace(0.9, 10, 100)
initial_params = np.concatenate([T_guess, P_guess])
# Define bounds for the parameters if needed
bounds = [(0, None)] * len(initial_params)  # Assuming non-negative values for simplicity

for i, spc in enumerate(list(Compounds.keys())):

    print(spc)

    species_arr = x_sol[i * Nt:(i + 1) * Nt]
    ind = np.argmax(species_arr)
    obs_selection = obs_spec[ind]

    theoretical_spectra = [generateSingleRef(Compounds[spc], T, P, wv_obs) for T, P in zip(T_values, P_values)]

    # Optimize the cost function using scipy's minimize function
    result = minimize(cost_function, initial_params, args=(obs_selection,theoretical_spectra), bounds=[(273, 473)] * len(T_guess) + [(0.9, 10)] * len(P_guess))
    optimized_params = result.x
    optimized_T = optimized_params[:len(T_guess)]
    optimized_P = optimized_params[len(T_guess):]

    print("Optimized T:", optimized_T)
    print("Optimized P:", optimized_P)



# # Define broadening and regularization constants
# regularisation_constant = 10**(-3)

# broad_array = np.logspace(-6,-1, 60)

# ref_spec_base, obs_spec, wv_obs = generateData_optimisation(Compounds, base_path + dataset, 0, T, P, dataset)

# ref_spec_base = np.nan_to_num(ref_spec_base)
# obs_spec = np.nan_to_num(obs_spec)

# obs_spec = obs_spec[:, ~np.all(ref_spec_base == 0, axis=0)]
# ref_spec_base = ref_spec_base[:, ~np.all(ref_spec_base == 0, axis=0)]

# ref_spec, Compounds, Lass = lasso_inversion_opt(ref_spec_base, obs_spec, Compounds)

# t_steps = [random.randint(0, obs_spec.shape[0]) for _ in range(10)]

# obs_spec = obs_spec[t_steps,:]

# for i, key in enumerate(Compounds):

#     print("Finding optimal spectra for ", key)
    
#     mol_arr = getReferenceMatrix_opt(Compounds[key], T, P, wv_obs, broad_array, key)

#     Lasso_eval = []

#     for arr in mol_arr:

#         reference_spectra = ref_spec_base

#         reference_spectra[i] = np.nan_to_num(arr[~np.all(ref_spec_base == 0, axis=0)])

#         S = np.array([s[~np.all(reference_spectra == 0, axis=0)] for s in obs_spec])
#         reference_spectra = np.array(reference_spectra[:, ~np.all(reference_spectra == 0, axis=0)])

#         Lasso_eval.append(lasso_inversion_opt2(reference_spectra, S, Compounds))

#     # Find minima
#     ind = np.where([x['RMSE'] for x in Lasso_eval] == [x['RMSE'] for x in Lasso_eval].min())
#     print(key, ind, mol_arr[ind])
#     print([x['RMSE'] for x in Lasso_eval])
