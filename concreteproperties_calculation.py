from concreteproperties.concrete_section import ConcreteSection
from concreteproperties.material import Concrete, SteelBar
from concreteproperties.pre import add_bar
import concreteproperties.stress_strain_profile as ssp
from sectionproperties.pre.library import rectangular_section
import numpy as np
import json
import os
import matplotlib.pyplot as plt
from concreteproperties.results import MomentCurvatureResults
from concreteproperties.post import si_kn_m, si_n_mm


class CompositeSectionBuilder:
    """Builder for saving analysis results from ConcreteSection objects."""
    
    def __init__(self):
        pass
    
    def save_gross_properties(self, section, output_dir=".", filename="1_gross_properties.json"):
        """Calculate and save gross properties."""
        
        gross_props = section.get_gross_properties()
        
        properties = {
            'area': float(gross_props.e_a),
            'perimeter': float(gross_props.perimeter),
            'mass': float(gross_props.mass),
            'centroid': {
                'cx': float(gross_props.cx),
                'cy': float(gross_props.cy)
            },
            'geometric_centroid': {
                'cx_gross': float(gross_props.cx_gross),
                'cy_gross': float(gross_props.cy_gross)
            },
            'second_moments_global': {
                'e_ixx_g': float(gross_props.e_ixx_g),
                'e_iyy_g': float(gross_props.e_iyy_g),
                'e_ixy_g': float(gross_props.e_ixy_g)
            },
            'second_moments_centroidal': {
                'e_ixx_c': float(gross_props.e_ixx_c),
                'e_iyy_c': float(gross_props.e_iyy_c),
                'e_ixy_c': float(gross_props.e_ixy_c)
            },
            'principal_axis': {
                'e_i11': float(gross_props.e_i11),
                'e_i22': float(gross_props.e_i22),
                'phi': float(gross_props.phi)
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(properties, f, indent=2)
        
        print(f"✓ Gross properties saved: {json_path}")
        return json_path
    
    def save_transformed_gross_properties(self, section, reference_elastic_modulus,
                                         output_dir=".", filename="2_transformed_gross_properties.json"):
        """Calculate and save transformed gross properties."""
        
        transformed_props = section.get_transformed_gross_properties(elastic_modulus=reference_elastic_modulus)
        
        properties = {
            'reference_elastic_modulus': float(reference_elastic_modulus),
            'area': float(transformed_props.area),
            'first_moments': {
                'qx': float(transformed_props.qx),
                'qy': float(transformed_props.qy)
            },
            'second_moments_global': {
                'ixx_g': float(transformed_props.ixx_g),
                'iyy_g': float(transformed_props.iyy_g),
                'ixy_g': float(transformed_props.ixy_g)
            },
            'second_moments_centroidal': {
                'ixx_c': float(transformed_props.ixx_c),
                'iyy_c': float(transformed_props.iyy_c),
                'ixy_c': float(transformed_props.ixy_c)
            },
            'principal_moments': {
                'i11': float(transformed_props.i11),
                'i22': float(transformed_props.i22)
            },
            'section_moduli_centroidal': {
                'zxx_plus': float(transformed_props.zxx_plus),
                'zxx_minus': float(transformed_props.zxx_minus),
                'zyy_plus': float(transformed_props.zyy_plus),
                'zyy_minus': float(transformed_props.zyy_minus)
            },
            'section_moduli_principal': {
                'z11_plus': float(transformed_props.z11_plus),
                'z11_minus': float(transformed_props.z11_minus),
                'z22_plus': float(transformed_props.z22_plus),
                'z22_minus': float(transformed_props.z22_minus)
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(properties, f, indent=2)
        
        print(f"✓ Transformed gross properties saved: {json_path}")
        return json_path
    
    def save_cracked_properties_sagging(self, section, output_dir=".", 
                                       filename="3_cracked_properties_sagging.json"):
        """Calculate and save cracked properties for sagging moment."""
        
        cracked_results = section.calculate_cracked_properties(theta=0)
        
        properties = {
            'analysis_type': 'sagging',
            'theta_rad': 0.0,
            'cracking_moment_Nmm': float(cracked_results.m_cr),
            'neutral_axis_depth_mm': float(cracked_results.d_nc),
            'cracked_second_moments_centroidal': {
                'E_Iuu_cr': float(cracked_results.e_iuu_cr)
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(properties, f, indent=2)
        
        print(f"✓ Cracked properties (sagging) saved: {json_path}")
        return json_path
    
    def save_cracked_properties_hogging(self, section, output_dir=".", 
                                       filename="4_cracked_properties_hogging.json"):
        """Calculate and save cracked properties for hogging moment."""
        
        cracked_results = section.calculate_cracked_properties(theta=np.pi)
        
        properties = {
            'analysis_type': 'hogging',
            'theta_rad': float(np.pi),
            'cracking_moment_Nmm': float(cracked_results.m_cr),
            'neutral_axis_depth_mm': float(cracked_results.d_nc),
            'cracked_second_moments_centroidal': {
                'E_Iuu_cr': float(cracked_results.e_iuu_cr)
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(properties, f, indent=2)
        
        print(f"✓ Cracked properties (hogging) saved: {json_path}")
        return json_path
    
    def save_transformed_cracked_properties_sagging(self, section, reference_elastic_modulus,
                                                   output_dir=".", 
                                                   filename="5_transformed_cracked_properties_sagging.json"):
        """Calculate and save transformed cracked properties for sagging moment."""
        
        cracked_results = section.calculate_cracked_properties(theta=0)
        cracked_results.calculate_transformed_properties(elastic_modulus=reference_elastic_modulus)
        
        properties = {
            'analysis_type': 'sagging',
            'reference_elastic_modulus': float(reference_elastic_modulus),
            'cracking_moment_Nmm': float(cracked_results.m_cr),
            'neutral_axis_depth_mm': float(cracked_results.d_nc),
            'transformed_area_mm2': float(cracked_results.a_cr),
            'transformed_second_moments_centroidal': {
                'Iuu_cr': float(cracked_results.iuu_cr)
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(properties, f, indent=2)
        
        print(f"✓ Transformed cracked properties (sagging) saved: {json_path}")
        return json_path
    
    def save_transformed_cracked_properties_hogging(self, section, reference_elastic_modulus,
                                                   output_dir=".", 
                                                   filename="6_transformed_cracked_properties_hogging.json"):
        """Calculate and save transformed cracked properties for hogging moment."""
        
        cracked_results = section.calculate_cracked_properties(theta=np.pi)
        cracked_results.calculate_transformed_properties(elastic_modulus=reference_elastic_modulus)
        
        properties = {
            'analysis_type': 'hogging',
            'reference_elastic_modulus': float(reference_elastic_modulus),
            'cracking_moment_Nmm': float(cracked_results.m_cr),
            'neutral_axis_depth_mm': float(cracked_results.d_nc),
            'transformed_area_mm2': float(cracked_results.a_cr),
            'transformed_second_moments_centroidal': {
                'Iuu_cr': float(cracked_results.iuu_cr)
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(properties, f, indent=2)
        
        print(f"✓ Transformed cracked properties (hogging) saved: {json_path}")
        return json_path
    
    def save_specific_cracked_results(self, section, output_dir=".", 
                                     filename="7_specific_cracked_results.json"):
        """Save specific cracked results (M_cr, d_nc, I_cr) for both sagging and hogging."""
        
        cracked_sag = section.calculate_cracked_properties(theta=0)
        cracked_hog = section.calculate_cracked_properties(theta=np.pi)
        
        # Need to calculate transformed properties to get iuu_cr (non-weighted)
        # Use a reference E (doesn't matter which since we just want the ratio to work out)
        cracked_sag.calculate_transformed_properties(elastic_modulus=30e3)
        cracked_hog.calculate_transformed_properties(elastic_modulus=30e3)
        
        results = {
            'sagging': {
                'M_cr_kNm': float(cracked_sag.m_cr / 1e6),
                'M_cr_Nmm': float(cracked_sag.m_cr),
                'd_nc_mm': float(cracked_sag.d_nc),
                'I_cr_mm4': float(cracked_sag.iuu_cr)
            },
            'hogging': {
                'M_cr_kNm': float(cracked_hog.m_cr / 1e6),
                'M_cr_Nmm': float(cracked_hog.m_cr),
                'd_nc_mm': float(cracked_hog.d_nc),
                'I_cr_mm4': float(cracked_hog.iuu_cr)
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"✓ Specific cracked results saved: {json_path}")
        print(f"\nSAGGING: M_cr={results['sagging']['M_cr_kNm']:.2f} kN·m, d_nc={results['sagging']['d_nc_mm']:.2f} mm")
        print(f"HOGGING: M_cr={results['hogging']['M_cr_kNm']:.2f} kN·m, d_nc={results['hogging']['d_nc_mm']:.2f} mm")
        
        return json_path
    
    def plot_cracked_geometries(self, section, output_dir=".", 
                               sagging_filename="8_cracked_geometry_sagging.png",
                               hogging_filename="9_cracked_geometry_hogging.png",
                               dpi=300):
        """Plot and save cracked geometries for sagging and hogging moments."""
        
        saved_files = {}
        os.makedirs(output_dir, exist_ok=True)
        
        cracked_sag = section.calculate_cracked_properties(theta=0)
        ax = cracked_sag.plot_cracked_geometries(labels=[], cp=False, legend=False)
        fig = ax.get_figure()
        sagging_path = os.path.join(output_dir, sagging_filename)
        fig.savefig(sagging_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        saved_files['sagging'] = sagging_path
        print(f"✓ Cracked geometry (sagging) saved: {sagging_path}")
        
        cracked_hog = section.calculate_cracked_properties(theta=np.pi)
        ax = cracked_hog.plot_cracked_geometries(labels=[], cp=False, legend=False)
        fig = ax.get_figure()
        hogging_path = os.path.join(output_dir, hogging_filename)
        fig.savefig(hogging_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        saved_files['hogging'] = hogging_path
        print(f"✓ Cracked geometry (hogging) saved: {hogging_path}")
        
        return saved_files
    
    def perform_moment_curvature_analysis(self, section, theta=0, n=0, 
                                         kappa_inc=2.5e-7, kappa_mult=2.0,
                                         delta_m_min=0.15, kappa_inc_max=5e-6,
                                         progress_bar=True):
        """Perform moment-curvature analysis on the section.
        
        Args:
            section: ConcreteSection object
            theta: Angle of bending (radians)
            n: Axial force (positive = compression, negative = tension)
            kappa_inc: Initial curvature increment
            kappa_mult: Multiplier for adaptive curvature increment
            delta_m_min: Minimum moment change to trigger adaptive curvature
            kappa_inc_max: Maximum curvature increment
            progress_bar: Show progress bar
            
        Returns:
            MomentCurvatureResults object
        """
        print(f"Performing moment-curvature analysis (theta={theta:.3f} rad, n={n:.2e} N)...")
        
        results = section.moment_curvature_analysis(
            theta=theta,
            n=n,
            kappa_inc=kappa_inc,
            kappa_mult=kappa_mult,
            delta_m_min=delta_m_min,
            kappa_inc_max=kappa_inc_max,
            progress_bar=progress_bar
        )
        
        print(f"✓ Moment-curvature analysis completed: {len(results.kappa)} points calculated")
        print(f"  Ultimate moment: {results.m_xy[-1]/1e6:.2f} kN·m")
        print(f"  Ultimate curvature: {results.kappa[-1]:.6f}")
        
        return results
    
    def save_moment_curvature_results(self, results, output_dir=".", 
                                      filename="10_moment_curvature_results.json"):
        """Save moment-curvature analysis results to JSON."""
        
        # Handle axial force - it might be a list or a single value
        if hasattr(results, 'n'):
            if isinstance(results.n, (list, np.ndarray)) and len(results.n) > 0:
                n_value = float(results.n[0]) if len(results.n) > 0 else 0.0
            else:
                n_value = float(results.n) if results.n is not None else 0.0
        else:
            n_value = 0.0
        
        # Build data dictionary with only available attributes
        data = {
            'analysis_parameters': {
                'theta_rad': float(results.theta),
                'n_target_N': float(results.n_target) if hasattr(results, 'n_target') else n_value,
                'n_axial_N': n_value,
                'num_points': len(results.kappa),
                'ultimate_moment_Nmm': float(results.m_xy[-1]),
                'ultimate_curvature': float(results.kappa[-1])
            },
            'curvature_data': {
                'kappa': [float(k) for k in results.kappa],
                'm_xy': [float(m) for m in results.m_xy],
                'm_x': [float(m) for m in results.m_x],
                'm_y': [float(m) for m in results.m_y],
                'n': [float(n_val) for n_val in results.n],
                'convergence': [float(c) for c in results.convergence] if hasattr(results, 'convergence') else []
            }
        }
        
        # Add failure geometry info if it exists
        if hasattr(results, 'failure_geometry') and results.failure_geometry is not None:
            try:
                data['failure_info'] = {
                    'failure_geometry_material': str(results.failure_geometry.material.name) 
                    if hasattr(results.failure_geometry, 'material') and hasattr(results.failure_geometry.material, 'name')
                    else "Unknown"
                }
            except:
                data['failure_info'] = {
                    'failure_geometry': "Available but could not be serialized"
                }
        
        # Key points
        data['key_points'] = {
            'cracking_point': {
                'index': self._find_cracking_point(results),
                'moment_Nmm': None  # We'll need to calculate this differently
            },
            'yield_point': {
                'index': self._find_yield_point(results),
            },
            'ultimate_point': {
                'index': len(results.kappa) - 1,
                'moment_Nmm': float(results.m_xy[-1]),
                'curvature': float(results.kappa[-1])
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Moment-curvature results saved: {json_path}")
        return json_path
    
    def _find_cracking_point(self, results, tolerance=0.05):
        """Find the cracking point in moment-curvature results."""
        if len(results.kappa) < 3:
            return None
        
        # Look for significant change in stiffness (cracking)
        for i in range(2, len(results.kappa)):
            delta_m1 = results.m_xy[i-1] - results.m_xy[i-2]
            delta_m2 = results.m_xy[i] - results.m_xy[i-1]
            
            if delta_m1 > 0 and abs(delta_m2/delta_m1 - 1) > tolerance:
                return i-1
        
        return None
    
    def _find_yield_point(self, results, tolerance=0.02):
        """Find the yield point in moment-curvature results."""
        if len(results.kappa) < 3:
            return None
        
        # Look for plateau in moment (yielding)
        for i in range(2, len(results.kappa)):
            delta_m1 = results.m_xy[i-1] - results.m_xy[i-2]
            delta_m2 = results.m_xy[i] - results.m_xy[i-1]
            
            if delta_m1 > 0 and abs(delta_m2/delta_m1) < tolerance:
                return i-1
        
        return None
    
    
    def plot_moment_curvature_single(self, results, output_dir=".", 
                                    filename="11_moment_curvature_plot.png",
                                    dpi=300, units=si_kn_m):
        """Plot and save single moment-curvature diagram."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Create our own plot instead of modifying the built-in one
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot the moment-curvature curve
        ax.plot(results.kappa, np.array(results.m_xy)/1e6, '-o', markersize=4)
        
        # Add annotations for key points
        crack_idx = self._find_cracking_point(results)
        yield_idx = self._find_yield_point(results)
        
        if crack_idx is not None:
            ax.plot(results.kappa[crack_idx], results.m_xy[crack_idx]/1e6, 
                   'ro', markersize=8, label='Cracking')
        
        if yield_idx is not None:
            ax.plot(results.kappa[yield_idx], results.m_xy[yield_idx]/1e6, 
                   'go', markersize=8, label='Yielding')
        
        # Ultimate point
        ax.plot(results.kappa[-1], results.m_xy[-1]/1e6, 
               'ko', markersize=8, label='Ultimate')
        
        ax.set_xlabel('Curvature [-]')
        ax.set_ylabel('Bending Moment [kN.m]')
        ax.set_title(f'Moment-Curvature (θ={np.degrees(results.theta):.1f}°)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plot_path = os.path.join(output_dir, filename)
        fig.savefig(plot_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        
        print(f"✓ Moment-curvature plot saved: {plot_path}")
        return plot_path

    def plot_multiple_moment_curvature(self, results_list, labels, output_dir=".", 
                                      filename="12_multiple_moment_curvature_comparison.png",
                                      dpi=300, units=si_kn_m):
        """Plot and save comparison of multiple moment-curvature diagrams."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot each result
        for results, label in zip(results_list, labels):
            ax.plot(results.kappa, np.array(results.m_xy)/1e6, 
                   '-', linewidth=2, label=label)
        
        ax.set_xlabel('Curvature [-]')
        ax.set_ylabel('Bending Moment [kN.m]')
        ax.set_title('Moment-Curvature Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plot_path = os.path.join(output_dir, filename)
        fig.savefig(plot_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        
        print(f"✓ Multiple moment-curvature comparison saved: {plot_path}")
        return plot_path
    
    def plot_stress_strain_profiles(self, concrete_materials, steel_materials, 
                                   output_dir=".", dpi=300):
        """Plot and save stress-strain profiles for materials."""
        
        os.makedirs(output_dir, exist_ok=True)
        saved_files = []
        
        # Plot concrete stress-strain profiles
        for idx, conc in enumerate(concrete_materials):
            fig, ax = plt.subplots(figsize=(8, 6))
            
            try:
                conc.stress_strain_profile.plot_stress_strain(
                    ax=ax,
                    title=f"{conc.name} Stress-Strain Profile",
                    eng=True,
                    units=si_n_mm
                )
                
                plot_path = os.path.join(output_dir, f"13_concrete_stress_strain_{idx+1}.png")
                fig.savefig(plot_path, dpi=dpi, bbox_inches='tight')
                saved_files.append(plot_path)
                print(f"✓ Concrete stress-strain profile saved: {plot_path}")
                
            except Exception as e:
                print(f"✗ Could not plot concrete stress-strain profile: {e}")
            
            plt.close(fig)
        
        # Plot steel stress-strain profiles
        for idx, steel in enumerate(steel_materials):
            fig, ax = plt.subplots(figsize=(8, 6))
            
            try:
                steel.stress_strain_profile.plot_stress_strain(
                    ax=ax,
                    title=f"{steel.name} Stress-Strain Profile",
                    eng=True,
                    units=si_n_mm
                )
                
                plot_path = os.path.join(output_dir, f"14_steel_stress_strain_{idx+1}.png")
                fig.savefig(plot_path, dpi=dpi, bbox_inches='tight')
                saved_files.append(plot_path)
                print(f"✓ Steel stress-strain profile saved: {plot_path}")
                
            except Exception as e:
                print(f"✗ Could not plot steel stress-strain profile: {e}")
            
            plt.close(fig)
        
        return saved_files
    
    def save_detailed_moment_curvature_summary(self, results_list, labels, 
                                              output_dir=".", 
                                              filename="15_moment_curvature_summary.json"):
        """Save detailed summary of moment-curvature analyses."""
        
        summary = {
            'analyses': [],
            'comparison': {}
        }
        
        for results, label in zip(results_list, labels):
            # Handle axial force
            if hasattr(results, 'n'):
                if isinstance(results.n, (list, np.ndarray)) and len(results.n) > 0:
                    n_value = float(results.n[0]) if len(results.n) > 0 else 0.0
                else:
                    n_value = float(results.n) if results.n is not None else 0.0
            else:
                n_value = 0.0
            
            # Get n_target if available
            n_target = float(results.n_target) if hasattr(results, 'n_target') else n_value
            
            analysis_data = {
                'label': label,
                'theta_rad': float(results.theta),
                'n_target_N': n_target,
                'n_axial_N': n_value,
                'ultimate_moment_Nmm': float(results.m_xy[-1]),
                'ultimate_moment_kNm': float(results.m_xy[-1] / 1e6),
                'ultimate_curvature': float(results.kappa[-1]),
                'num_points': len(results.kappa),
                'cracking_point_index': self._find_cracking_point(results),
                'yield_point_index': self._find_yield_point(results),
                'stiffness_initial': float(results.m_xy[1] / results.kappa[1]) if len(results.kappa) > 1 else None,
                'stiffness_cracked': self._calculate_cracked_stiffness(results)
            }
            summary['analyses'].append(analysis_data)
        
        # Add comparison metrics
        if len(results_list) > 1:
            summary['comparison'] = {
                'moment_ratio': float(results_list[-1].m_xy[-1] / results_list[0].m_xy[-1]),
                'curvature_ratio': float(results_list[-1].kappa[-1] / results_list[0].kappa[-1])
            }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ Detailed moment-curvature summary saved: {json_path}")
        return json_path
    
    def _calculate_cracked_stiffness(self, results):
        """Calculate cracked section stiffness from moment-curvature results."""
        crack_idx = self._find_cracking_point(results)
        if crack_idx and crack_idx < len(results.kappa) - 2:
            # Use points after cracking to estimate cracked stiffness
            start_idx = crack_idx + 1
            end_idx = min(crack_idx + 5, len(results.kappa) - 1)
            
            if end_idx > start_idx:
                kappa_range = results.kappa[start_idx:end_idx]
                moment_range = results.m_xy[start_idx:end_idx]
                
                # Linear regression for stiffness
                if len(kappa_range) > 1:
                    poly = np.polyfit(kappa_range, moment_range, 1)
                    return float(poly[0])  # Slope = stiffness
        
        return None
    
    def analyze_with_varying_parameters(self, section, output_dir="."):
        """Perform comprehensive moment-curvature analysis with varying parameters."""
        
        print("\n" + "="*60)
        print("COMPREHENSIVE MOMENT-CURVATURE ANALYSIS")
        print("="*60)
        
        # Analysis 1: Basic moment-curvature (sagging)
        print("\n1. Basic moment-curvature analysis (sagging, N=0):")
        mc_results_basic = self.perform_moment_curvature_analysis(
            section, theta=0, n=0, progress_bar=False
        )
        
        # Save basic results
        self.save_moment_curvature_results(
            mc_results_basic, output_dir, "10_moment_curvature_basic.json"
        )
        self.plot_moment_curvature_single(
            mc_results_basic, output_dir, "11_moment_curvature_basic.png"
        )
        
        # Analysis 2: Hogging moment
        print("\n2. Moment-curvature analysis (hogging, N=0):")
        mc_results_hogging = self.perform_moment_curvature_analysis(
            section, theta=np.pi, n=0, progress_bar=False
        )
        
        # Analysis 3: With compression
        print("\n3. Moment-curvature analysis (sagging, with compression):")
        # Calculate 0.2f'cAg for typical 40 MPa concrete
        concrete_area = 300 * 600 + 400 * 150  # Web + flange area in mm²
        n_comp = 0.2 * 40 * concrete_area  # 0.2f'cAg in N
        mc_results_comp = self.perform_moment_curvature_analysis(
            section, theta=0, n=n_comp, progress_bar=False
        )
        
        # Analysis 4: With tension
        print("\n4. Moment-curvature analysis (sagging, with tension):")
        mc_results_tension = self.perform_moment_curvature_analysis(
            section, theta=0, n=-1000e3, progress_bar=False  # -1000 kN tension
        )
        
        # Save all results in one file
        all_results = [mc_results_basic, mc_results_hogging, mc_results_comp, mc_results_tension]
        labels = ["Sagging (N=0)", "Hogging (N=0)", f"Sagging (N={n_comp/1e6:.1f} kN)", "Sagging (N=-1000 kN)"]
        
        self.save_detailed_moment_curvature_summary(
            all_results, labels, output_dir, "15_moment_curvature_summary.json"
        )
        
        # Plot comparison
        self.plot_multiple_moment_curvature(
            all_results, labels, output_dir, "12_moment_curvature_comparison.png"
        )
        
        # Analysis 5: Fine-tuned analysis for better resolution
        print("\n5. Fine-tuned moment-curvature analysis:")
        mc_results_fine = self.perform_moment_curvature_analysis(
            section, theta=0, n=0,
            kappa_inc=1e-6,
            kappa_mult=1.25,
            delta_m_min=0.1,
            kappa_inc_max=2e-5,
            progress_bar=False
        )
        
        self.save_moment_curvature_results(
            mc_results_fine, output_dir, "16_moment_curvature_fine.json"
        )
        
        # Plot fine vs basic comparison
        self.plot_multiple_moment_curvature(
            [mc_results_basic, mc_results_fine], 
            ["Default parameters", "Fine-tuned parameters"],
            output_dir, 
            "17_fine_vs_default_comparison.png"
        )
        
        print("\n" + "="*60)
        print("MOMENT-CURVATURE ANALYSIS COMPLETE")
        print("="*60)
        
        return {
            'basic': mc_results_basic,
            'hogging': mc_results_hogging,
            'compression': mc_results_comp,
            'tension': mc_results_tension,
            'fine': mc_results_fine
        }

    def perform_ultimate_bending_analysis(self, section, theta=0, n=0, label=None):
        """Perform ultimate bending capacity analysis on the section.
        
        Args:
            section: ConcreteSection object
            theta: Angle of bending (radians)
            n: Axial force (positive = compression, negative = tension)
            label: Optional label for the analysis
            
        Returns:
            UltimateBendingResults object
        """
        print(f"Performing ultimate bending analysis (theta={theta:.3f} rad, n={n:.2e} N)...")
        
        results = section.ultimate_bending_capacity(theta=theta, n=n)
        
        # Add label if provided
        if label:
            results.label = label
        
        print(f"✓ Ultimate bending analysis completed")
        print(f"  Neutral axis depth: {results.d_n:.2f} mm")
        print(f"  Ultimate moment: {results.m_xy/1e6:.2f} kN·m")
        print(f"  Axial force: {results.n/1e3:.2f} kN")
        
        return results
    
    def save_ultimate_bending_results(self, results, output_dir=".", 
                                     filename="18_ultimate_bending_results.json"):
        """Save ultimate bending analysis results to JSON."""
        
        data = {
            'analysis_parameters': {
                'theta_rad': float(results.theta),
                'theta_deg': float(np.degrees(results.theta)),
                'n_axial_N': float(results.n),
                'label': results.label if hasattr(results, 'label') else None
            },
            'results': {
                'neutral_axis_depth_mm': float(results.d_n),
                'neutral_axis_parameter_k_u': float(results.k_u),
                'axial_force_N': float(results.n),
                'axial_force_kN': float(results.n / 1e3),
                'bending_moment_m_x_Nmm': float(results.m_x),
                'bending_moment_m_y_Nmm': float(results.m_y),
                'bending_moment_m_xy_Nmm': float(results.m_xy),
                'bending_moment_m_x_kNm': float(results.m_x / 1e6),
                'bending_moment_m_y_kNm': float(results.m_y / 1e6),
                'bending_moment_m_xy_kNm': float(results.m_xy / 1e6)
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Ultimate bending results saved: {json_path}")
        return json_path
    
    def analyze_ultimate_bending_capacities(self, section, output_dir="."):
        """Perform comprehensive ultimate bending capacity analysis."""
        
        print("\n" + "="*60)
        print("ULTIMATE BENDING CAPACITY ANALYSIS")
        print("="*60)
        
        # Analysis 1: Sagging moment (N=0)
        print("\n1. Ultimate bending capacity (sagging, N=0):")
        sag_results = self.perform_ultimate_bending_analysis(
            section, theta=0, n=0, label="Sagging (N=0)"
        )
        self.save_ultimate_bending_results(
            sag_results, output_dir, "18_ultimate_bending_sagging_N0.json"
        )
        
        # Analysis 2: Hogging moment (N=0)
        print("\n2. Ultimate bending capacity (hogging, N=0):")
        hog_results = self.perform_ultimate_bending_analysis(
            section, theta=np.pi, n=0, label="Hogging (N=0)"
        )
        self.save_ultimate_bending_results(
            hog_results, output_dir, "19_ultimate_bending_hogging_N0.json"
        )
        
        # Analysis 3: Weak axis bending (N=0)
        print("\n3. Ultimate bending capacity (weak axis, N=0):")
        weak_results = self.perform_ultimate_bending_analysis(
            section, theta=np.pi/2, n=0, label="Weak axis (N=0)"
        )
        self.save_ultimate_bending_results(
            weak_results, output_dir, "20_ultimate_bending_weak_axis_N0.json"
        )
        
        # Analysis 4-6: With axial compression
        n_comp = 5000e3  # 5000 kN compression
        print(f"\n4. Ultimate bending capacity (sagging, N={n_comp/1e3:.0f} kN):")
        sag_comp_results = self.perform_ultimate_bending_analysis(
            section, theta=0, n=n_comp, label=f"Sagging (N={n_comp/1e3:.0f} kN)"
        )
        self.save_ultimate_bending_results(
            sag_comp_results, output_dir, "21_ultimate_bending_sagging_comp.json"
        )
        
        print(f"\n5. Ultimate bending capacity (hogging, N={n_comp/1e3:.0f} kN):")
        hog_comp_results = self.perform_ultimate_bending_analysis(
            section, theta=np.pi, n=n_comp, label=f"Hogging (N={n_comp/1e3:.0f} kN)"
        )
        self.save_ultimate_bending_results(
            hog_comp_results, output_dir, "22_ultimate_bending_hogging_comp.json"
        )
        
        print(f"\n6. Ultimate bending capacity (weak axis, N={n_comp/1e3:.0f} kN):")
        weak_comp_results = self.perform_ultimate_bending_analysis(
            section, theta=np.pi/2, n=n_comp, label=f"Weak axis (N={n_comp/1e3:.0f} kN)"
        )
        self.save_ultimate_bending_results(
            weak_comp_results, output_dir, "23_ultimate_bending_weak_axis_comp.json"
        )
        
        # Analysis 7: With axial tension
        n_tension = -1000e3  # -1000 kN tension
        print(f"\n7. Ultimate bending capacity (sagging, N={n_tension/1e3:.0f} kN):")
        sag_tension_results = self.perform_ultimate_bending_analysis(
            section, theta=0, n=n_tension, label=f"Sagging (N={n_tension/1e3:.0f} kN)"
        )
        self.save_ultimate_bending_results(
            sag_tension_results, output_dir, "24_ultimate_bending_sagging_tension.json"
        )
        
        # Create summary of all analyses
        all_results = [
            sag_results, hog_results, weak_results,
            sag_comp_results, hog_comp_results, weak_comp_results,
            sag_tension_results
        ]
        
        self.save_ultimate_bending_summary(all_results, output_dir)
        
        print("\n" + "="*60)
        print("ULTIMATE BENDING ANALYSIS COMPLETE")
        print("="*60)
        
        return all_results
    
    def save_ultimate_bending_summary(self, results_list, output_dir=".",
                                     filename="25_ultimate_bending_summary.json"):
        """Save summary of all ultimate bending analyses."""
        
        summary = {
            'analyses': [],
            'comparison': {
                'sagging_vs_hogging_ratio': None,
                'compression_effect': None,
                'tension_effect': None
            }
        }
        
        for results in results_list:
            analysis_data = {
                'label': results.label if hasattr(results, 'label') else "Unlabeled",
                'theta_rad': float(results.theta),
                'theta_deg': float(np.degrees(results.theta)),
                'n_axial_N': float(results.n),
                'd_n_mm': float(results.d_n),
                'k_u': float(results.k_u),
                'm_xy_Nmm': float(results.m_xy),
                'm_xy_kNm': float(results.m_xy / 1e6),
                'm_x_kNm': float(results.m_x / 1e6),
                'm_y_kNm': float(results.m_y / 1e6)
            }
            summary['analyses'].append(analysis_data)
        
        # Calculate comparison metrics
        if len(results_list) >= 2:
            # Sagging vs hogging ratio (N=0)
            sag_n0 = next((r for r in results_list if r.label == "Sagging (N=0)"), None)
            hog_n0 = next((r for r in results_list if r.label == "Hogging (N=0)"), None)
            
            if sag_n0 and hog_n0:
                summary['comparison']['sagging_vs_hogging_ratio'] = float(
                    sag_n0.m_xy / hog_n0.m_xy
                )
            
            # Compression effect on sagging moment
            sag_comp = next((r for r in results_list if "Sagging (N=5000" in str(r.label)), None)
            if sag_n0 and sag_comp:
                summary['comparison']['compression_effect'] = {
                    'moment_increase': float((sag_comp.m_xy - sag_n0.m_xy) / sag_n0.m_xy),
                    'moment_ratio': float(sag_comp.m_xy / sag_n0.m_xy)
                }
            
            # Tension effect on sagging moment
            sag_tension = next((r for r in results_list if "Sagging (N=-1000" in str(r.label)), None)
            if sag_n0 and sag_tension:
                summary['comparison']['tension_effect'] = {
                    'moment_decrease': float((sag_n0.m_xy - sag_tension.m_xy) / sag_n0.m_xy),
                    'moment_ratio': float(sag_tension.m_xy / sag_n0.m_xy)
                }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ Ultimate bending summary saved: {json_path}")
        
        # Print key findings
        print("\nKEY FINDINGS:")
        if sag_n0 and hog_n0:
            print(f"  • Sagging/Hogging ratio: {summary['comparison']['sagging_vs_hogging_ratio']:.2f}")
        if 'compression_effect' in summary['comparison'] and summary['comparison']['compression_effect']:
            eff = summary['comparison']['compression_effect']
            print(f"  • Compression (5000 kN) increases sagging moment by {eff['moment_increase']*100:.1f}%")
        if 'tension_effect' in summary['comparison'] and summary['comparison']['tension_effect']:
            eff = summary['comparison']['tension_effect']
            print(f"  • Tension (1000 kN) decreases sagging moment by {eff['moment_decrease']*100:.1f}%")
        
        return json_path
    
    def plot_ultimate_bending_comparison(self, results_list, output_dir=".",
                                        filename="26_ultimate_bending_comparison.png",
                                        dpi=300):
        """Plot comparison of ultimate bending capacities."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Filter results for comparison (N=0 cases)
        n0_results = [r for r in results_list if abs(r.n) < 1e-3]
        
        if len(n0_results) < 3:
            print("✗ Not enough N=0 results for comparison plot")
            return None
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Plot 1: Moment capacities for different bending angles
        angles = [np.degrees(r.theta) for r in n0_results]
        moments = [r.m_xy/1e6 for r in n0_results]  # kN·m
        labels = [r.label if hasattr(r, 'label') else f"θ={a:.0f}°" 
                 for r, a in zip(n0_results, angles)]
        
        bars1 = ax1.bar(range(len(angles)), moments)
        ax1.set_xlabel('Bending Direction')
        ax1.set_ylabel('Ultimate Moment Capacity [kN·m]')
        ax1.set_title('Ultimate Bending Capacities (N=0)')
        ax1.set_xticks(range(len(angles)))
        ax1.set_xticklabels([f"θ={a:.0f}°" for a in angles])
        ax1.grid(True, alpha=0.3)
        
        # Add values on top of bars
        for bar, moment in zip(bars1, moments):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02*max(moments),
                    f'{moment:.0f}', ha='center', va='bottom')
        
        # Plot 2: Effect of axial force on sagging moment
        sag_results = [r for r in results_list if "Sagging" in str(r.label)]
        if len(sag_results) >= 3:
            axial_forces = [r.n/1e3 for r in sag_results]  # kN
            sag_moments = [r.m_xy/1e6 for r in sag_results]  # kN·m
            sag_labels = [r.label for r in sag_results]
            
            ax2.plot(axial_forces, sag_moments, 'o-', linewidth=2, markersize=8)
            ax2.set_xlabel('Axial Force [kN]')
            ax2.set_ylabel('Ultimate Moment Capacity [kN·m]')
            ax2.set_title('Effect of Axial Force on Sagging Moment')
            ax2.grid(True, alpha=0.3)
            
            # Add labels to points
            for i, (force, moment, label) in enumerate(zip(axial_forces, sag_moments, sag_labels)):
                if "N=0" in label:
                    ax2.annotate("N=0", (force, moment), 
                                textcoords="offset points", 
                                xytext=(0,10), ha='center')
                elif "5000" in label:
                    ax2.annotate("N=5000 kN", (force, moment), 
                                textcoords="offset points", 
                                xytext=(0,10), ha='center')
                elif "-1000" in label:
                    ax2.annotate("N=-1000 kN", (force, moment), 
                                textcoords="offset points", 
                                xytext=(0,10), ha='center')
        
        plt.tight_layout()
        plot_path = os.path.join(output_dir, filename)
        fig.savefig(plot_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        
        print(f"✓ Ultimate bending comparison plot saved: {plot_path}")
        return plot_path

    def perform_moment_interaction_analysis(self, section, theta=0, 
                                           limits=None, control_points=None,
                                           labels=None, n_points=24,
                                           n_spacing=None, max_comp=None,
                                           max_comp_labels=None, progress_bar=True):
        """Perform moment interaction analysis on the section.
        
        Args:
            section: ConcreteSection object
            theta: Angle of bending (radians)
            limits: List of control points defining start and end of interaction diagram
            control_points: Additional control points to include
            labels: Labels for limits and control_points
            n_points: Number of points to compute
            n_spacing: Overrides n_points, generates diagram with equally spaced axial loads
            max_comp: Maximum compressive force to limit diagram
            max_comp_labels: Labels for max_comp intersection points
            progress_bar: Show progress bar
            
        Returns:
            MomentInteractionResults object
        """
        print(f"Performing moment interaction analysis (theta={theta:.3f} rad)...")
        
        results = section.moment_interaction_diagram(
            theta=theta,
            limits=limits,
            control_points=control_points,
            labels=labels,
            n_points=n_points,
            n_spacing=n_spacing,
            max_comp=max_comp,
            max_comp_labels=max_comp_labels,
            progress_bar=progress_bar
        )
        
        print(f"✓ Moment interaction analysis completed: {len(results.results)} points calculated")
        print(f"  Maximum axial compression: {max([r.n for r in results.results])/1e3:.1f} kN")
        print(f"  Maximum bending moment: {max([abs(r.m_xy) for r in results.results])/1e6:.1f} kN·m")
        
        return results
    
    def save_moment_interaction_results(self, results, output_dir=".", 
                                       filename="27_moment_interaction_results.json"):
        """Save moment interaction analysis results to JSON."""
        
        # Sort results first
        results.sort_results()
        
        data = {
            'analysis_parameters': {
                'num_points': len(results.results),
                'sorted': True
            },
            'interaction_data': [],
            'key_points': {
                'pure_compression': None,
                'pure_bending': None,
                'balanced_point': None,
                'pure_tension': None
            }
        }
        
        # Save all interaction points
        for idx, res in enumerate(results.results):
            point_data = {
                'index': idx,
                'label': res.label if hasattr(res, 'label') else None,
                'theta_rad': float(res.theta),
                'd_n_mm': float(res.d_n),
                'k_u': float(res.k_u),
                'n_N': float(res.n),
                'n_kN': float(res.n / 1e3),
                'm_x_Nmm': float(res.m_x),
                'm_y_Nmm': float(res.m_y),
                'm_xy_Nmm': float(res.m_xy),
                'm_x_kNm': float(res.m_x / 1e6),
                'm_y_kNm': float(res.m_y / 1e6),
                'm_xy_kNm': float(res.m_xy / 1e6)
            }
            data['interaction_data'].append(point_data)
            
            # Identify key points by label
            if res.label:
                label_lower = res.label.lower()
                if 'pure comp' in label_lower or 'kappa0' in label_lower:
                    data['key_points']['pure_compression'] = idx
                elif 'pure bend' in label_lower or 'n=0' in label_lower:
                    data['key_points']['pure_bending'] = idx
                elif 'balance' in label_lower or 'fy=1' in label_lower:
                    data['key_points']['balanced_point'] = idx
                elif 'pure tens' in label_lower:
                    data['key_points']['pure_tension'] = idx
        
        # If key points not found by label, find them by characteristics
        if data['key_points']['pure_compression'] is None:
            # Pure compression has max axial force and near-zero moment
            max_n_idx = max(range(len(results.results)), 
                          key=lambda i: results.results[i].n)
            data['key_points']['pure_compression'] = max_n_idx
        
        if data['key_points']['pure_bending'] is None:
            # Pure bending has near-zero axial force
            min_n_abs_idx = min(range(len(results.results)), 
                              key=lambda i: abs(results.results[i].n))
            data['key_points']['pure_bending'] = min_n_abs_idx
        
        if data['key_points']['balanced_point'] is None:
            # Balanced point is where extreme steel reaches yield
            # This is more complex to identify automatically
            pass
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Moment interaction results saved: {json_path}")
        return json_path
    
    def analyze_moment_interaction(self, section, output_dir="."):
        """Perform comprehensive moment interaction analysis."""
        
        print("\n" + "="*60)
        print("MOMENT INTERACTION DIAGRAM ANALYSIS")
        print("="*60)
        
        # Analysis 1: Basic moment interaction diagram (sagging)
        print("\n1. Basic moment interaction diagram (sagging):")
        mi_basic = self.perform_moment_interaction_analysis(
            section, theta=0, progress_bar=False
        )
        self.save_moment_interaction_results(
            mi_basic, output_dir, "27_moment_interaction_basic.json"
        )
        
        # Analysis 2: Hogging moment interaction
        print("\n2. Moment interaction diagram (hogging):")
        mi_hogging = self.perform_moment_interaction_analysis(
            section, theta=np.pi, progress_bar=False
        )
        self.save_moment_interaction_results(
            mi_hogging, output_dir, "28_moment_interaction_hogging.json"
        )
        
        # Analysis 3: Weak axis moment interaction
        print("\n3. Moment interaction diagram (weak axis):")
        mi_weak = self.perform_moment_interaction_analysis(
            section, theta=np.pi/2, progress_bar=False
        )
        self.save_moment_interaction_results(
            mi_weak, output_dir, "29_moment_interaction_weak_axis.json"
        )
        
        # Analysis 4: Advanced moment interaction with control points
        print("\n4. Advanced moment interaction diagram with control points:")
        
        # First get the maximum axial capacity from the basic analysis
        max_axial_capacity = max([r.n for r in mi_basic.results])
        print(f"  Maximum axial capacity: {max_axial_capacity/1e3:.1f} kN")
        print(f"  Using 85% for max_comp: {max_axial_capacity * 0.85/1e3:.1f} kN")
        
        # Then use it in the advanced analysis
        mi_advanced = self.perform_moment_interaction_analysis(
            section, theta=0,
            limits=[("kappa0", 0.0), ("d_n", 1e-6)],
            control_points=[
                ("D", 1.0),      # Concrete decompression
                ("fy", 0.0),     # Steel decompression  
                ("fy", 0.5),     # 50% yield strain
                ("fy", 1.0),     # Balanced point (100% yield)
                ("d_n", 200.0),  # Neutral axis at 200mm
                ("N", 0.0),      # Pure bending
            ],
            labels=["NA", "I", "C", "D", "E", "F", "G", "H"],
            n_spacing=36,
            max_comp=max_axial_capacity * 0.85,  # Use actual max capacity
            max_comp_labels=["A", "B"],
            progress_bar=False
        )
        
        self.save_moment_interaction_results(
            mi_advanced, output_dir, "30_moment_interaction_advanced.json"
        )
        
        # Create plots
        self.plot_moment_interaction_diagrams(
            [mi_basic, mi_hogging, mi_weak, mi_advanced],
            ["Sagging", "Hogging", "Weak Axis", "Advanced"],
            output_dir
        )
        
        # Create comparison summary
        self.save_moment_interaction_summary(
            [mi_basic, mi_hogging, mi_weak],
            output_dir
        )
        
        print("\n" + "="*60)
        print("MOMENT INTERACTION ANALYSIS COMPLETE")
        print("="*60)
        
        return {
            'basic': mi_basic,
            'hogging': mi_hogging,
            'weak': mi_weak,
            'advanced': mi_advanced
        }

    def plot_moment_interaction_diagrams(self, results_list, labels, output_dir=".",
                                        filename_prefix="moment_interaction"):
        """Plot multiple moment interaction diagrams."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Plot 1: Individual diagrams
        for idx, (results, label) in enumerate(zip(results_list, labels)):
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Get data points
            n_list, m_list = results.get_results_lists(moment="m_xy")
            n_kN = [n/1e3 for n in n_list]  # Convert to kN
            m_kNm = [m/1e6 for m in m_list]  # Convert to kN·m
            
            # Plot the diagram
            ax.plot(m_kNm, n_kN, 'o-', markersize=4, linewidth=2)
            
            # Add labels for special points if they exist
            for i, res in enumerate(results.results):
                if hasattr(res, 'label') and res.label:
                    ax.annotate(res.label, 
                              (m_list[i]/1e6, n_list[i]/1e3),
                              textcoords="offset points",
                              xytext=(5,5), 
                              fontsize=8)
            
            ax.set_xlabel('Bending Moment [kN·m]')
            ax.set_ylabel('Axial Force [kN]')
            ax.set_title(f'Moment Interaction Diagram: {label}')
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)
            
            plot_path = os.path.join(output_dir, f"31_{filename_prefix}_{label.lower().replace(' ', '_')}.png")
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            print(f"✓ {label} interaction diagram saved: {plot_path}")
        
        # Plot 2: Comparison of basic diagrams
        if len(results_list) >= 3:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot first three (basic, hogging, weak axis)
            for results, label in zip(results_list[:3], labels[:3]):
                n_list, m_list = results.get_results_lists(moment="m_xy")
                n_kN = [n/1e3 for n in n_list]
                m_kNm = [m/1e6 for m in m_list]
                ax.plot(m_kNm, n_kN, '-', linewidth=2, label=label)
            
            ax.set_xlabel('Bending Moment [kN·m]')
            ax.set_ylabel('Axial Force [kN]')
            ax.set_title('Moment Interaction Diagram Comparison')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)
            
            plot_path = os.path.join(output_dir, "32_moment_interaction_comparison.png")
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            print(f"✓ Interaction diagram comparison saved: {plot_path}")
        
        # Plot 3: Positive vs Negative bending
        if len(results_list) >= 2:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Use built-in method for better formatting
            try:
                from concreteproperties.results import MomentInteractionResults
                MomentInteractionResults.plot_multiple_diagrams(
                    moment_interaction_results=[results_list[0], results_list[1]],
                    labels=[labels[0], labels[1]],
                    fmt='-',
                    eng=True,
                    units=si_kn_m,
                    ax=ax
                )
            except:
                # Fallback to manual plotting
                for results, label in zip(results_list[:2], labels[:2]):
                    n_list, m_list = results.get_results_lists(moment="m_xy")
                    n_kN = [n/1e3 for n in n_list]
                    m_kNm = [abs(m)/1e6 for m in m_list]  # Use absolute for comparison
                    ax.plot(m_kNm, n_kN, '-', linewidth=2, label=label)
                
                ax.set_xlabel('Bending Moment [kN·m]')
                ax.set_ylabel('Axial Force [kN]')
                ax.set_title('Positive vs Negative Bending Interaction')
                ax.legend()
                ax.grid(True, alpha=0.3)
            
            plot_path = os.path.join(output_dir, "33_positive_vs_negative.png")
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            print(f"✓ Positive vs negative comparison saved: {plot_path}")
    
    def save_moment_interaction_summary(self, results_list, output_dir=".",
                                       filename="34_moment_interaction_summary.json"):
        """Save summary of moment interaction analyses."""
        
        summary = {
            'analyses': [],
            'capacity_comparison': {},
            'interaction_envelopes': {}
        }
        
        for idx, results in enumerate(results_list):
            n_list, m_list = results.get_results_lists(moment="m_xy")
            
            # Find key capacities
            pure_bending_idx = min(range(len(n_list)), key=lambda i: abs(n_list[i]))
            max_comp_idx = max(range(len(n_list)), key=lambda i: n_list[i])
            max_tension_idx = min(range(len(n_list)), key=lambda i: n_list[i])
            max_moment_idx = max(range(len(m_list)), key=lambda i: abs(m_list[i]))
            
            analysis_data = {
                'index': idx,
                'num_points': len(n_list),
                'pure_bending': {
                    'm_xy_kNm': float(m_list[pure_bending_idx] / 1e6),
                    'n_kN': float(n_list[pure_bending_idx] / 1e3)
                },
                'max_compression': {
                    'm_xy_kNm': float(m_list[max_comp_idx] / 1e6),
                    'n_kN': float(n_list[max_comp_idx] / 1e3)
                },
                'max_tension': {
                    'm_xy_kNm': float(m_list[max_tension_idx] / 1e6),
                    'n_kN': float(n_list[max_tension_idx] / 1e3)
                },
                'max_moment': {
                    'm_xy_kNm': float(m_list[max_moment_idx] / 1e6),
                    'n_kN': float(n_list[max_moment_idx] / 1e3)
                },
                'interaction_ratio': float(abs(m_list[max_moment_idx]) / abs(m_list[pure_bending_idx]))
            }
            summary['analyses'].append(analysis_data)
        
        # Calculate comparison metrics
        if len(results_list) >= 3:
            # Compare sagging vs hogging pure bending capacities
            sag_pure = summary['analyses'][0]['pure_bending']['m_xy_kNm']
            hog_pure = summary['analyses'][1]['pure_bending']['m_xy_kNm']
            weak_pure = summary['analyses'][2]['pure_bending']['m_xy_kNm']
            
            summary['capacity_comparison'] = {
                'sagging_vs_hogging_ratio': float(sag_pure / hog_pure),
                'sagging_vs_weak_ratio': float(sag_pure / weak_pure),
                'hogging_vs_weak_ratio': float(hog_pure / weak_pure)
            }
            
            # Calculate interaction envelopes
            summary['interaction_envelopes'] = {
                'maximum_moment_envelope': float(max([a['max_moment']['m_xy_kNm'] for a in summary['analyses']])),
                'maximum_compression_envelope': float(max([a['max_compression']['n_kN'] for a in summary['analyses']])),
                'maximum_tension_envelope': float(min([a['max_tension']['n_kN'] for a in summary['analyses']]))
            }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ Moment interaction summary saved: {json_path}")
        
        # Print key findings
        print("\nKEY INTERACTION FINDINGS:")
        if len(results_list) >= 3:
            comp = summary['capacity_comparison']
            print(f"  • Sagging/Hogging pure bending ratio: {comp['sagging_vs_hogging_ratio']:.2f}")
            print(f"  • Sagging/Weak axis pure bending ratio: {comp['sagging_vs_weak_ratio']:.2f}")
            
            env = summary['interaction_envelopes']
            print(f"  • Maximum moment capacity: {env['maximum_moment_envelope']:.1f} kN·m")
            print(f"  • Maximum compression capacity: {env['maximum_compression_envelope']:.1f} kN")
            print(f"  • Maximum tension capacity: {env['maximum_tension_envelope']:.1f} kN")
        
        return json_path
    
    def check_design_point(self, results, n_design, m_design, moment="m_xy"):
        """Check if a design point lies within the moment interaction diagram.
        
        Args:
            results: MomentInteractionResults object
            n_design: Design axial force (N)
            m_design: Design bending moment (N·mm)
            moment: Which moment to check ("m_x", "m_y", or "m_xy")
            
        Returns:
            Dictionary with check results
        """
        is_inside = results.point_in_diagram(n=n_design, m=m_design, moment=moment)
        
        result = {
            'design_point': {
                'n_N': float(n_design),
                'n_kN': float(n_design / 1e3),
                'm_Nmm': float(m_design),
                'm_kNm': float(m_design / 1e6),
                'moment_type': moment
            },
            'within_capacity': bool(is_inside),
            'safety_margin': None,
            'closest_point': None
        }
        
        if not is_inside:
            # Find closest point on interaction diagram
            n_list, m_list = results.get_results_lists(moment=moment)
            
            # Calculate distances to all points
            distances = []
            for n, m in zip(n_list, m_list):
                # Normalized distance (weight axial and moment differently)
                dist = np.sqrt(
                    ((n - n_design) / max(abs(n_list)))**2 + 
                    ((m - m_design) / max(abs(m_list)))**2
                )
                distances.append(dist)
            
            closest_idx = np.argmin(distances)
            result['closest_point'] = {
                'index': int(closest_idx),
                'n_N': float(n_list[closest_idx]),
                'n_kN': float(n_list[closest_idx] / 1e3),
                'm_Nmm': float(m_list[closest_idx]),
                'm_kNm': float(m_list[closest_idx] / 1e6)
            }
        
        return result

    def perform_biaxial_bending_analysis(self, section, n=0, n_points=24, 
                                        progress_bar=True):
        """Perform biaxial bending analysis on the section.
        
        Args:
            section: ConcreteSection object
            n: Axial force (positive = compression, negative = tension)
            n_points: Number of points to compute
            progress_bar: Show progress bar
            
        Returns:
            BiaxialBendingResults object
        """
        print(f"Performing biaxial bending analysis (n={n:.2e} N)...")
        
        results = section.biaxial_bending_diagram(
            n=n,
            n_points=n_points,
            progress_bar=progress_bar
        )
        
        print(f"✓ Biaxial bending analysis completed: {len(results.results)} points calculated")
        print(f"  Axial force: {results.n/1e3:.1f} kN")
        
        return results
    
    def save_biaxial_bending_results(self, results, output_dir=".", 
                                    filename="35_biaxial_bending_results.json"):
        """Save biaxial bending analysis results to JSON."""
        
        data = {
            'analysis_parameters': {
                'n_axial_N': float(results.n),
                'n_axial_kN': float(results.n / 1e3),
                'num_points': len(results.results)
            },
            'biaxial_data': [],
            'capacity_envelope': {
                'max_m_x': None,
                'max_m_y': None,
                'min_m_x': None,
                'min_m_y': None
            }
        }
        
        m_x_max = m_y_max = -float('inf')
        m_x_min = m_y_min = float('inf')
        
        # Save all biaxial bending points
        for idx, res in enumerate(results.results):
            point_data = {
                'index': idx,
                'theta_rad': float(res.theta),
                'theta_deg': float(np.degrees(res.theta)),
                'd_n_mm': float(res.d_n),
                'k_u': float(res.k_u),
                'n_N': float(res.n),
                'm_x_Nmm': float(res.m_x),
                'm_y_Nmm': float(res.m_y),
                'm_xy_Nmm': float(res.m_xy),
                'm_x_kNm': float(res.m_x / 1e6),
                'm_y_kNm': float(res.m_y / 1e6),
                'm_xy_kNm': float(res.m_xy / 1e6)
            }
            data['biaxial_data'].append(point_data)
            
            # Track envelope
            m_x_max = max(m_x_max, res.m_x)
            m_y_max = max(m_y_max, res.m_y)
            m_x_min = min(m_x_min, res.m_x)
            m_y_min = min(m_y_min, res.m_y)
        
        data['capacity_envelope'] = {
            'max_m_x_Nmm': float(m_x_max),
            'max_m_y_Nmm': float(m_y_max),
            'min_m_x_Nmm': float(m_x_min),
            'min_m_y_Nmm': float(m_y_min),
            'max_m_x_kNm': float(m_x_max / 1e6),
            'max_m_y_kNm': float(m_y_max / 1e6),
            'min_m_x_kNm': float(m_x_min / 1e6),
            'min_m_y_kNm': float(m_y_min / 1e6)
        }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Biaxial bending results saved: {json_path}")
        return json_path
    
    def analyze_biaxial_bending(self, section, output_dir="."):
        """Perform comprehensive biaxial bending analysis."""
        
        print("\n" + "="*60)
        print("BIAXIAL BENDING DIAGRAM ANALYSIS")
        print("="*60)
        
        # First, get decompression points from moment interaction
        print("\n1. Determining decompression points...")
        mi_x = section.moment_interaction_diagram(progress_bar=False)
        mi_y = section.moment_interaction_diagram(theta=np.pi/2, progress_bar=False)
        
        # Get decompression points (second point in sorted list)
        mi_x.sort_results()
        mi_y.sort_results()
        
        n_decomp_x = mi_x.results[1].n if len(mi_x.results) > 1 else 0
        n_decomp_y = mi_y.results[1].n if len(mi_y.results) > 1 else 0
        
        print(f"  • Decompression point for M_x: {n_decomp_x/1e3:.1f} kN")
        print(f"  • Decompression point for M_y: {n_decomp_y/1e3:.1f} kN")
        
        # Analysis 2: Pure bending (N=0)
        print("\n2. Biaxial bending diagram (pure bending, N=0):")
        bb_pure = self.perform_biaxial_bending_analysis(
            section, n=0, n_points=24, progress_bar=False
        )
        self.save_biaxial_bending_results(
            bb_pure, output_dir, "35_biaxial_bending_pure.json"
        )
        
        # Analysis 3: With moderate compression
        print("\n3. Biaxial bending diagram (moderate compression, N=1000 kN):")
        bb_comp1 = self.perform_biaxial_bending_analysis(
            section, n=1000e3, n_points=24, progress_bar=False
        )
        self.save_biaxial_bending_results(
            bb_comp1, output_dir, "36_biaxial_bending_comp1.json"
        )
        
        # Analysis 4: With higher compression
        print("\n4. Biaxial bending diagram (higher compression, N=3000 kN):")
        bb_comp2 = self.perform_biaxial_bending_analysis(
            section, n=3000e3, n_points=24, progress_bar=False
        )
        self.save_biaxial_bending_results(
            bb_comp2, output_dir, "37_biaxial_bending_comp2.json"
        )
        
        # Analysis 5: Near decompression point
        n_decomp_avg = (n_decomp_x + n_decomp_y) / 2
        print(f"\n5. Biaxial bending diagram (near decompression, N={n_decomp_avg/1e3:.0f} kN):")
        bb_decomp = self.perform_biaxial_bending_analysis(
            section, n=n_decomp_avg * 0.9, n_points=24, progress_bar=False  # 90% of decompression
        )
        self.save_biaxial_bending_results(
            bb_decomp, output_dir, "38_biaxial_bending_decomp.json"
        )
        
        # Analysis 6: With tension
        print("\n6. Biaxial bending diagram (tension, N=-500 kN):")
        bb_tension = self.perform_biaxial_bending_analysis(
            section, n=-500e3, n_points=24, progress_bar=False
        )
        self.save_biaxial_bending_results(
            bb_tension, output_dir, "39_biaxial_bending_tension.json"
        )
        
        # Create multiple axial load levels for 3D plot
        print("\n7. Generating multiple axial levels for 3D visualization...")
        n_levels = 5
        n_list = np.linspace(0, n_decomp_avg * 0.95, n_levels)
        bb_multi = []
        
        for i, n_val in enumerate(n_list):
            bb = self.perform_biaxial_bending_analysis(
                section, n=n_val, n_points=24, progress_bar=False
            )
            bb_multi.append(bb)
            self.save_biaxial_bending_results(
                bb, output_dir, f"40_biaxial_bending_level_{i+1}.json"
            )
        
        # Create plots
        self.plot_biaxial_bending_diagrams(
            [bb_pure, bb_comp1, bb_comp2, bb_decomp, bb_tension],
            ["N=0", "N=1000 kN", "N=3000 kN", f"N={n_decomp_avg/1e3:.0f} kN", "N=-500 kN"],
            output_dir
        )
        
        # Create 3D plot
        self.plot_biaxial_3d_diagram(bb_multi, output_dir)
        
        # Create summary
        self.save_biaxial_bending_summary(
            [bb_pure, bb_comp1, bb_comp2, bb_decomp, bb_tension],
            output_dir
        )
        
        print("\n" + "="*60)
        print("BIAXIAL BENDING ANALYSIS COMPLETE")
        print("="*60)
        
        return {
            'pure': bb_pure,
            'comp1': bb_comp1,
            'comp2': bb_comp2,
            'decomp': bb_decomp,
            'tension': bb_tension,
            'multi': bb_multi
        }
    
    def plot_biaxial_bending_diagrams(self, results_list, labels, output_dir=".",
                                     filename_prefix="biaxial_bending"):
        """Plot multiple biaxial bending diagrams."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Plot 1: Individual diagrams
        for idx, (results, label) in enumerate(zip(results_list, labels)):
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Get data points
            m_x_list, m_y_list = results.get_results_lists()
            m_x_kNm = [m/1e6 for m in m_x_list]  # Convert to kN·m
            m_y_kNm = [m/1e6 for m in m_y_list]  # Convert to kN·m
            
            # Plot the diagram
            ax.plot(m_x_kNm, m_y_kNm, 'o-', markersize=4, linewidth=2)
            
            # Add quadrants and center point
            ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)
            ax.plot(0, 0, 'ko', markersize=8)  # Center point
            
            # Add labels for quadrants
            ax.text(0.02, 0.98, 'Quadrant I', transform=ax.transAxes, 
                   verticalalignment='top', fontsize=10)
            ax.text(0.98, 0.98, 'Quadrant II', transform=ax.transAxes, 
                   verticalalignment='top', horizontalalignment='right', fontsize=10)
            ax.text(0.02, 0.02, 'Quadrant IV', transform=ax.transAxes, 
                   verticalalignment='bottom', fontsize=10)
            ax.text(0.98, 0.02, 'Quadrant III', transform=ax.transAxes, 
                   verticalalignment='bottom', horizontalalignment='right', fontsize=10)
            
            ax.set_xlabel('Bending Moment M_x [kN·m]')
            ax.set_ylabel('Bending Moment M_y [kN·m]')
            ax.set_title(f'Biaxial Bending Diagram: {label}')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal', adjustable='box')
            
            plot_path = os.path.join(output_dir, f"41_{filename_prefix}_{label.lower().replace(' ', '_').replace('=', '')}.png")
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            print(f"✓ {label} biaxial diagram saved: {plot_path}")
        
        # Plot 2: Comparison of all diagrams (2D)
        if len(results_list) > 1:
            try:
                # Use built-in method for better formatting
                from concreteproperties.results import BiaxialBendingResults
                
                fig, ax = plt.subplots(figsize=(10, 8))
                BiaxialBendingResults.plot_multiple_diagrams_2d(
                    biaxial_bending_results=results_list,
                    labels=labels,
                    fmt='-',
                    eng=True,
                    units=si_kn_m,
                    ax=ax
                )
                ax.set_title('Biaxial Bending Diagrams Comparison')
                ax.set_aspect('equal', adjustable='box')
                
                plot_path = os.path.join(output_dir, "42_biaxial_bending_comparison_2d.png")
                fig.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close(fig)
                print(f"✓ Biaxial diagram 2D comparison saved: {plot_path}")
                
            except Exception as e:
                print(f"✗ Could not create 2D comparison plot: {e}")
                # Fallback to manual plotting
                fig, ax = plt.subplots(figsize=(10, 8))
                for results, label in zip(results_list, labels):
                    m_x_list, m_y_list = results.get_results_lists()
                    m_x_kNm = [m/1e6 for m in m_x_list]
                    m_y_kNm = [m/1e6 for m in m_y_list]
                    ax.plot(m_x_kNm, m_y_kNm, '-', linewidth=2, label=label)
                
                ax.set_xlabel('Bending Moment M_x [kN·m]')
                ax.set_ylabel('Bending Moment M_y [kN·m]')
                ax.set_title('Biaxial Bending Diagrams Comparison')
                ax.legend()
                ax.grid(True, alpha=0.3)
                ax.set_aspect('equal', adjustable='box')
                ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
                ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)
                
                plot_path = os.path.join(output_dir, "42_biaxial_bending_comparison_2d.png")
                fig.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close(fig)
                print(f"✓ Biaxial diagram 2D comparison saved: {plot_path}")
    
    def plot_biaxial_3d_diagram(self, results_list, output_dir=".",
                               filename="43_biaxial_bending_3d.png"):
        """Plot 3D biaxial bending diagram."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Use built-in method for 3D plot
            from concreteproperties.results import BiaxialBendingResults
            
            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection='3d')
            
            # Plot each result
            for idx, results in enumerate(results_list):
                m_x_list, m_y_list = results.get_results_lists()
                m_x_kNm = np.array(m_x_list) / 1e6
                m_y_kNm = np.array(m_y_list) / 1e6
                n_kN = results.n / 1e3
                
                # Create array of constant N for this level
                n_array = np.full_like(m_x_kNm, n_kN)
                
                ax.plot(m_x_kNm, m_y_kNm, n_array, '-', linewidth=2, 
                       label=f'N={n_kN:.0f} kN')
            
            ax.set_xlabel('Bending Moment M_x [kN·m]')
            ax.set_ylabel('Bending Moment M_y [kN·m]')
            ax.set_zlabel('Axial Force N [kN]')
            ax.set_title('3D Biaxial Bending Interaction Diagram')
            ax.legend()
            
            # Adjust view angle for better visualization
            ax.view_init(elev=20, azim=45)
            
            plot_path = os.path.join(output_dir, filename)
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            print(f"✓ 3D biaxial diagram saved: {plot_path}")
            
        except Exception as e:
            print(f"✗ Could not create 3D plot: {e}")
            return None
    
    def save_biaxial_bending_summary(self, results_list, output_dir=".",
                                    filename="44_biaxial_bending_summary.json"):
        """Save summary of biaxial bending analyses."""
        
        summary = {
            'analyses': [],
            'envelope_comparison': {},
            'axial_effect_analysis': {}
        }
        
        for idx, results in enumerate(results_list):
            m_x_list, m_y_list = results.get_results_lists()
            
            # Calculate envelope metrics
            m_x_max = max(m_x_list)
            m_y_max = max(m_y_list)
            m_x_min = min(m_x_list)
            m_y_min = min(m_y_list)
            
            # Calculate area of biaxial envelope (approximation)
            if len(m_x_list) > 2:
                # Use shoelace formula for polygon area
                area = 0.5 * abs(sum(
                    m_x_list[i] * m_y_list[(i+1) % len(m_y_list)] - 
                    m_y_list[i] * m_x_list[(i+1) % len(m_x_list)]
                    for i in range(len(m_x_list))
                ))
            else:
                area = 0
            
            analysis_data = {
                'index': idx,
                'n_N': float(results.n),
                'n_kN': float(results.n / 1e3),
                'num_points': len(m_x_list),
                'envelope': {
                    'm_x_max_Nmm': float(m_x_max),
                    'm_y_max_Nmm': float(m_y_max),
                    'm_x_min_Nmm': float(m_x_min),
                    'm_y_min_Nmm': float(m_y_min),
                    'm_x_max_kNm': float(m_x_max / 1e6),
                    'm_y_max_kNm': float(m_y_max / 1e6),
                    'm_x_min_kNm': float(m_x_min / 1e6),
                    'm_y_min_kNm': float(m_y_min / 1e6),
                    'envelope_area_N2mm2': float(area),
                    'envelope_area_kN2m2': float(area / 1e12)
                },
                'aspect_ratios': {
                    'm_x_range_to_m_y_range': float((max(m_x_list)-min(m_x_list)) / (max(m_y_list)-min(m_y_list))) 
                    if max(m_y_list)-min(m_y_list) != 0 else float('inf'),
                    'max_moment_ratio': float(max(abs(m) for m in m_x_list) / max(abs(m) for m in m_y_list)) 
                    if max(abs(m) for m in m_y_list) != 0 else float('inf')
                }
            }
            summary['analyses'].append(analysis_data)
        
        # Calculate effect of axial force on envelope
        if len(results_list) >= 2:
            # Find pure bending case
            pure_idx = next((i for i, a in enumerate(summary['analyses']) if abs(a['n_N']) < 1e-3), 0)
            pure_envelope = summary['analyses'][pure_idx]['envelope']
            
            summary['axial_effect_analysis'] = {
                'pure_bending_reference': {
                    'n_kN': summary['analyses'][pure_idx]['n_kN'],
                    'max_m_x_kNm': pure_envelope['m_x_max_kNm'],
                    'max_m_y_kNm': pure_envelope['m_y_max_kNm'],
                    'envelope_area_kN2m2': pure_envelope['envelope_area_kN2m2']
                }
            }
            
            # Compare other cases to pure bending
            for idx, analysis in enumerate(summary['analyses']):
                if idx != pure_idx:
                    key = f"n_{analysis['n_kN']:.0f}_kN"
                    summary['axial_effect_analysis'][key] = {
                        'm_x_change_percent': float((analysis['envelope']['m_x_max_kNm'] - pure_envelope['m_x_max_kNm']) / 
                                                   pure_envelope['m_x_max_kNm'] * 100),
                        'm_y_change_percent': float((analysis['envelope']['m_y_max_kNm'] - pure_envelope['m_y_max_kNm']) / 
                                                   pure_envelope['m_y_max_kNm'] * 100),
                        'area_change_percent': float((analysis['envelope']['envelope_area_kN2m2'] - pure_envelope['envelope_area_kN2m2']) / 
                                                    pure_envelope['envelope_area_kN2m2'] * 100)
                    }
        
        # Calculate envelope comparison
        if len(results_list) > 0:
            summary['envelope_comparison'] = {
                'overall_max_m_x_kNm': max(a['envelope']['m_x_max_kNm'] for a in summary['analyses']),
                'overall_max_m_y_kNm': max(a['envelope']['m_y_max_kNm'] for a in summary['analyses']),
                'overall_min_m_x_kNm': min(a['envelope']['m_x_min_kNm'] for a in summary['analyses']),
                'overall_min_m_y_kNm': min(a['envelope']['m_y_min_kNm'] for a in summary['analyses']),
                'largest_envelope_area_kN2m2': max(a['envelope']['envelope_area_kN2m2'] for a in summary['analyses'])
            }
        
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ Biaxial bending summary saved: {json_path}")
        
        # Print key findings
        print("\nKEY BIAXIAL FINDINGS:")
        if 'axial_effect_analysis' in summary and len(summary['axial_effect_analysis']) > 1:
            pure_ref = summary['axial_effect_analysis']['pure_bending_reference']
            print(f"  • Pure bending envelope area: {pure_ref['envelope_area_kN2m2']:.1f} kN²·m²")
            
            for key, effect in summary['axial_effect_analysis'].items():
                if key != 'pure_bending_reference':
                    n_val = key.split('_')[1]
                    print(f"  • N={n_val} kN: M_x {effect['m_x_change_percent']:+.1f}%, "
                          f"M_y {effect['m_y_change_percent']:+.1f}%, "
                          f"Area {effect['area_change_percent']:+.1f}%")
        
        return json_path
    
    def check_biaxial_design_point(self, results, m_x_design, m_y_design):
        """Check if a biaxial design point lies within the biaxial bending diagram.
        
        Args:
            results: BiaxialBendingResults object
            m_x_design: Design bending moment about x-axis (N·mm)
            m_y_design: Design bending moment about y-axis (N·mm)
            
        Returns:
            Dictionary with check results
        """
        is_inside = results.point_in_diagram(m_x=m_x_design, m_y=m_y_design)
        
        result = {
            'design_point': {
                'm_x_Nmm': float(m_x_design),
                'm_y_Nmm': float(m_y_design),
                'm_x_kNm': float(m_x_design / 1e6),
                'm_y_kNm': float(m_y_design / 1e6),
                'n_N': float(results.n),
                'n_kN': float(results.n / 1e3)
            },
            'within_capacity': bool(is_inside),
            'closest_point': None,
            'interaction_ratio': None
        }
        
        if not is_inside:
            # Find closest point on interaction diagram
            m_x_list, m_y_list = results.get_results_lists()
            
            # Calculate distances to all points
            distances = []
            for m_x, m_y in zip(m_x_list, m_y_list):
                # Euclidean distance normalized by max moments
                m_x_max = max(abs(m) for m in m_x_list)
                m_y_max = max(abs(m) for m in m_y_list)
                dist = np.sqrt(
                    ((m_x - m_x_design) / m_x_max)**2 + 
                    ((m_y - m_y_design) / m_y_max)**2
                )
                distances.append(dist)
            
            closest_idx = np.argmin(distances)
            result['closest_point'] = {
                'index': int(closest_idx),
                'm_x_Nmm': float(m_x_list[closest_idx]),
                'm_y_Nmm': float(m_y_list[closest_idx]),
                'm_x_kNm': float(m_x_list[closest_idx] / 1e6),
                'm_y_kNm': float(m_y_list[closest_idx] / 1e6),
                'distance_normalized': float(distances[closest_idx])
            }
        
        # Calculate interaction ratio (Bresler's formula approximation)
        m_x_list, m_y_list = results.get_results_lists()
        if m_x_list and m_y_list:
            # Find maximum moments for each axis
            m_x_max = max(abs(m) for m in m_x_list)
            # m_y_max = max(abs(abs(m) for m in m_y_list))
            m_y_max = max(abs(m) for m in m_y_list)
            
            if m_x_max > 0 and m_y_max > 0:
                # Simple interaction ratio (conservative)
                interaction_ratio = (abs(m_x_design)/m_x_max) + (abs(m_y_design)/m_y_max)
                result['interaction_ratio'] = float(interaction_ratio)
        
        return result

    def perform_stress_analysis(self, section, output_dir="."):
        """Perform comprehensive stress analysis including all types.
        
        Args:
            section: ConcreteSection object
            output_dir: Output directory for results
            
        Returns:
            Dictionary containing all stress analysis results
        """
        print("\n" + "="*60)
        print("COMPREHENSIVE STRESS ANALYSIS")
        print("="*60)
        
        all_results = {}
        
        # 1. Elastic Uncracked Stress Analysis
        print("\n1. Performing elastic uncracked stress analysis...")
        uncracked_results = self.perform_elastic_uncracked_analysis(section, output_dir)
        all_results['uncracked'] = uncracked_results
        
        # 2. Elastic Cracked Stress Analysis
        print("\n2. Performing elastic cracked stress analysis...")
        cracked_results = self.perform_elastic_cracked_analysis(section, output_dir)
        all_results['cracked'] = cracked_results
        
        # 3. Service Stress Analysis
        print("\n3. Performing service stress analysis...")
        service_results = self.perform_service_stress_analysis(section, output_dir)
        all_results['service'] = service_results
        
        # 4. Ultimate Stress Analysis
        print("\n4. Performing ultimate stress analysis...")
        ultimate_results = self.perform_ultimate_stress_analysis(section, output_dir)
        all_results['ultimate'] = ultimate_results
        
        # 5. Create summary
        print("\n5. Creating stress analysis summary...")
        self.save_stress_analysis_summary(all_results, output_dir)
        
        print("\n" + "="*60)
        print("STRESS ANALYSIS COMPLETE")
        print("="*60)
        
        return all_results
    
    def perform_elastic_uncracked_analysis(self, section, output_dir="."):
        """Perform elastic uncracked stress analysis."""
        
        print("  a. Case 1: Pure bending about x-axis (Mx=50 kN·m)")
        uncr_stress_1 = section.calculate_uncracked_stress(m_x=50e6)
        
        print("  b. Case 2: Biaxial bending with axial (Mx=25 kN·m, My=35 kN·m, N=200 kN)")
        uncr_stress_2 = section.calculate_uncracked_stress(
            m_x=25e6, m_y=35e6, n=200e3
        )
        
        print("  c. Case 3: High moment (Mx=150 kN·m)")
        uncr_stress_3 = section.calculate_uncracked_stress(m_x=150e6)
        
        # Save results
        results = {
            'case1': uncr_stress_1,
            'case2': uncr_stress_2,
            'case3': uncr_stress_3
        }
        
        self.save_stress_results(results, 'uncracked', output_dir)
        self.plot_stress_results(results, 'uncracked', output_dir)
        
        return results
    
    def perform_elastic_cracked_analysis(self, section, output_dir="."):
        """Perform elastic cracked stress analysis."""
        
        # First perform cracking analysis
        print("  Performing cracking analysis...")
        cracked_res = section.calculate_cracked_properties(theta=0)
        print(f"    Cracking moment: {cracked_res.m_cr/1e6:.2f} kN·m")
        print(f"    Neutral axis depth: {cracked_res.d_nc:.2f} mm")
        
        # Calculate stresses at different moments
        moments = [
            cracked_res.m_cr * 0.5,      # 50% of cracking moment
            cracked_res.m_cr,            # Exactly at cracking
            cracked_res.m_cr * 1.5,      # 150% of cracking moment
            cracked_res.m_cr * 2.0       # 200% of cracking moment
        ]
        
        results = {'cracking_analysis': cracked_res}
        
        for i, moment in enumerate(moments):
            label = f"case{i+1}"
            print(f"  {label}: M = {moment/1e6:.1f} kN·m")
            stress_res = section.calculate_cracked_stress(
                cracked_results=cracked_res, m=moment
            )
            results[label] = stress_res
            
            # Verify equilibrium
            net_force = stress_res.sum_forces()
            net_moment = stress_res.sum_moments()[2]
            print(f"    Net force: {net_force/1e3:.2f} kN, "
                  f"Net moment: {net_moment/1e6:.2f} kN·m")
        
        # Save and plot results
        self.save_stress_results(results, 'cracked', output_dir)
        self.plot_stress_results(results, 'cracked', output_dir)
        
        return results
    
    def perform_service_stress_analysis(self, section, output_dir="."):
        """Perform service stress analysis using moment-curvature results."""
        
        print("  Performing moment-curvature analysis for service stresses...")
        mk_res = section.moment_curvature_analysis(
            kappa_inc=2.5e-7, progress_bar=False
        )
        
        # Get cracking moment for reference
        cracked_res = section.calculate_cracked_properties(theta=0)
        m_cr = cracked_res.m_cr
        
        # Define interesting stress points
        stress_inputs = [
            {"label": "below_crack", "m_or_k": "m", "val": m_cr * 0.7},
            {"label": "at_crack", "m_or_k": "m", "val": m_cr},
            {"label": "softening1", "m_or_k": "k", "val": 7.5e-7},
            {"label": "softening2", "m_or_k": "k", "val": 1.15e-6},
            {"label": "post_crack", "m_or_k": "m", "val": m_cr * 1.5},
            {"label": "yield_region", "m_or_k": "m", "val": m_cr * 2.5},
            {"label": "high_moment", "m_or_k": "m", "val": m_cr * 3.0}
        ]
        
        results = {'moment_curvature': mk_res}
        
        for s_in in stress_inputs:
            label = s_in["label"]
            print(f"  {label}: ", end="")
            
            if s_in["m_or_k"] == "m":
                moment = s_in["val"]
                print(f"M = {moment/1e6:.1f} kN·m")
                stress_res = section.calculate_service_stress(
                    moment_curvature_results=mk_res, m=moment
                )
            else:  # "k"
                kappa = s_in["val"]
                print(f"κ = {kappa:.2e}")
                stress_res = section.calculate_service_stress(
                    moment_curvature_results=mk_res, m=None, kappa=kappa
                )
                moment = stress_res.sum_moments()[2]
                print(f"    Corresponding moment: {moment/1e6:.1f} kN·m")
            
            results[label] = stress_res
        
        # Save and plot results
        self.save_stress_results(results, 'service', output_dir)
        self.plot_stress_results(results, 'service', output_dir)
        
        return results
    
    def perform_ultimate_stress_analysis(self, section, output_dir="."):
        """Perform ultimate stress analysis."""
        
        print("  Performing moment interaction analysis...")
        mi_res = section.moment_interaction_diagram(progress_bar=False)
        
        # Find key points from moment interaction
        mi_res.sort_results()
        
        # Pure bending point (near N=0)
        pure_bending_idx = min(range(len(mi_res.results)), 
                             key=lambda i: abs(mi_res.results[i].n))
        pure_bending = mi_res.results[pure_bending_idx]
        
        # Balanced point (approximate as point with max moment)
        max_moment_idx = max(range(len(mi_res.results)),
                           key=lambda i: abs(mi_res.results[i].m_xy))
        balanced_point = mi_res.results[max_moment_idx]
        
        # Decompression point (max compression with small moment)
        # Find point near max compression but with small moment
        sorted_by_n = sorted(mi_res.results, key=lambda r: r.n, reverse=True)
        decompression_point = None
        for res in sorted_by_n[:5]:  # Look at top 5 compression points
            if abs(res.m_xy) < 0.1 * balanced_point.m_xy:
                decompression_point = res
                break
        
        if decompression_point is None:
            decompression_point = sorted_by_n[0]  # Use pure compression
        
        print(f"  Pure bending: N={pure_bending.n/1e3:.0f} kN, "
              f"M={pure_bending.m_xy/1e6:.1f} kN·m")
        print(f"  Balanced point: N={balanced_point.n/1e3:.0f} kN, "
              f"M={balanced_point.m_xy/1e6:.1f} kN·m")
        print(f"  Decompression: N={decompression_point.n/1e3:.0f} kN, "
              f"M={decompression_point.m_xy/1e6:.1f} kN·m")
        
        # Calculate ultimate stresses for each point
        results = {'moment_interaction': mi_res}
        
        # Pure bending stresses
        print("  Calculating pure bending stresses...")
        ultimate_res_pure = section.ultimate_bending_capacity(
            n=pure_bending.n
        )
        ultimate_stress_pure = section.calculate_ultimate_stress(
            ultimate_results=ultimate_res_pure
        )
        results['pure_bending'] = {
            'ultimate_results': ultimate_res_pure,
            'stress_results': ultimate_stress_pure
        }
        
        # Balanced point stresses
        print("  Calculating balanced point stresses...")
        ultimate_res_bal = section.ultimate_bending_capacity(
            n=balanced_point.n
        )
        ultimate_stress_bal = section.calculate_ultimate_stress(
            ultimate_results=ultimate_res_bal
        )
        results['balanced'] = {
            'ultimate_results': ultimate_res_bal,
            'stress_results': ultimate_stress_bal
        }
        
        # Decompression point stresses
        print("  Calculating decompression point stresses...")
        ultimate_res_decomp = section.ultimate_bending_capacity(
            n=decompression_point.n
        )
        ultimate_stress_decomp = section.calculate_ultimate_stress(
            ultimate_results=ultimate_res_decomp
        )
        results['decompression'] = {
            'ultimate_results': ultimate_res_decomp,
            'stress_results': ultimate_stress_decomp
        }
        
        # Save and plot results
        self.save_stress_results(results, 'ultimate', output_dir)
        self.plot_stress_results(results, 'ultimate', output_dir)
        
        return results
    
    def save_stress_results(self, results_dict, analysis_type, output_dir="."):
        """Save stress analysis results to JSON."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        for key, results in results_dict.items():
            if key in ['moment_curvature', 'moment_interaction', 'cracking_analysis']:
                continue  # Skip non-stress results
                
            if isinstance(results, dict) and 'stress_results' in results:
                # For ultimate stress results which have nested structure
                stress_res = results['stress_results']
                ultimate_res = results['ultimate_results']
                
                data = self._extract_stress_data(stress_res)
                data['ultimate_parameters'] = {
                    'theta_rad': float(ultimate_res.theta),
                    'd_n_mm': float(ultimate_res.d_n),
                    'k_u': float(ultimate_res.k_u),
                    'n_N': float(ultimate_res.n),
                    'm_xy_Nmm': float(ultimate_res.m_xy)
                }
                
            elif hasattr(results, 'sum_forces'):  # It's a StressResult object
                data = self._extract_stress_data(results)
                
            else:
                continue  # Skip if not a stress result
            
            filename = f"45_{analysis_type}_stress_{key}.json"
            json_path = os.path.join(output_dir, filename)
            
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"    ✓ {key} stress results saved: {filename}")
    
    def _extract_stress_data(self, stress_result):
        """Extract data from StressResult object."""
        
        data = {
            'equilibrium_check': {
                'net_force_N': float(stress_result.sum_forces()),
                'net_moment_x_Nmm': float(stress_result.sum_moments()[0]),
                'net_moment_y_Nmm': float(stress_result.sum_moments()[1]),
                'net_moment_resultant_Nmm': float(stress_result.sum_moments()[2])
            },
            'concrete_stresses': {
                'min_stress_MPa': float(stress_result.get_concrete_stress_limits()[0]),
                'max_stress_MPa': float(stress_result.get_concrete_stress_limits()[1]),
                'num_sections': len(stress_result.concrete_analysis_sections)
            },
            'reinforcement_stresses': {
                'num_lumped_bars': len(stress_result.lumped_reinforcement_stresses),
                'num_meshed_sections': len(stress_result.meshed_reinforcement_sections)
            },
            'detailed_results': {}
        }
        
        # Add concrete section forces
        concrete_forces = []
        for i, (force, dx, dy) in enumerate(stress_result.concrete_forces):
            concrete_forces.append({
                'section': i,
                'force_N': float(force),
                'lever_arm_x_mm': float(dx),
                'lever_arm_y_mm': float(dy),
                'moment_x_Nmm': float(force * dy),
                'moment_y_Nmm': float(force * dx)
            })
        data['detailed_results']['concrete_forces'] = concrete_forces
        
        # Add reinforcement forces
        if stress_result.lumped_reinforcement_forces:
            reinf_forces = []
            for i, (force, dx, dy) in enumerate(stress_result.lumped_reinforcement_forces):
                reinf_forces.append({
                    'bar': i,
                    'force_N': float(force),
                    'stress_MPa': float(stress_result.lumped_reinforcement_stresses[i]),
                    'strain': float(stress_result.lumped_reinforcement_strains[i]),
                    'lever_arm_x_mm': float(dx),
                    'lever_arm_y_mm': float(dy),
                    'moment_x_Nmm': float(force * dy),
                    'moment_y_Nmm': float(force * dx)
                })
            data['detailed_results']['reinforcement_forces'] = reinf_forces
        
        return data
    
    def plot_stress_results(self, results_dict, analysis_type, output_dir="."):
        """Plot stress analysis results."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        plot_counter = 46  # Start from file number 46
        
        for key, results in results_dict.items():
            if key in ['moment_curvature', 'moment_interaction', 'cracking_analysis']:
                continue  # Skip non-stress results
                
            if isinstance(results, dict) and 'stress_results' in results:
                # For ultimate stress results
                stress_res = results['stress_results']
                ultimate_res = results['ultimate_results']
                title = f"{analysis_type.title()} Stress: {key.replace('_', ' ').title()}\n"
                title += f"N={ultimate_res.n/1e3:.0f} kN, M={ultimate_res.m_xy/1e6:.1f} kN·m"
                
            elif hasattr(results, 'sum_forces'):  # It's a StressResult object
                stress_res = results
                title = f"{analysis_type.title()} Stress: {key.replace('_', ' ').title()}"
                
                # Try to extract moment information
                net_moment = stress_res.sum_moments()[2]
                title += f"\nM={net_moment/1e6:.1f} kN·m"
                
            else:
                continue  # Skip if not a stress result
            
            # Create plot
            try:
                fig = plt.figure(figsize=(12, 8))
                ax = stress_res.plot_stress(
                    title=title,
                    conc_cmap="RdGy",
                    reinf_cmap="bwr",
                    eng=True,
                    units=si_kn_m,
                    render=False
                )
                
                filename = f"{plot_counter:02d}_{analysis_type}_stress_{key}.png"
                plot_path = os.path.join(output_dir, filename)
                fig.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close(fig)
                
                print(f"    ✓ {key} stress plot saved: {filename}")
                plot_counter += 1
                
            except Exception as e:
                print(f"    ✗ Could not create plot for {key}: {e}")
    
    def save_stress_analysis_summary(self, all_results, output_dir="."):
        """Save comprehensive stress analysis summary."""
        
        summary = {
            'analysis_types': ['uncracked', 'cracked', 'service', 'ultimate'],
            'key_findings': {},
            'stress_ranges': {},
            'equilibrium_checks': {}
        }
        
        # Analyze each type
        for analysis_type, results in all_results.items():
            summary['key_findings'][analysis_type] = []
            summary['stress_ranges'][analysis_type] = {}
            summary['equilibrium_checks'][analysis_type] = {}
            
            if analysis_type == 'uncracked':
                for key, stress_res in results.items():
                    if hasattr(stress_res, 'get_concrete_stress_limits'):
                        min_stress, max_stress = stress_res.get_concrete_stress_limits()
                        net_force = stress_res.sum_forces()
                        net_moment = stress_res.sum_moments()[2]
                        
                        summary['key_findings'][analysis_type].append({
                            'case': key,
                            'concrete_min_stress_MPa': float(min_stress),
                            'concrete_max_stress_MPa': float(max_stress),
                            'net_force_N': float(net_force),
                            'net_moment_Nmm': float(net_moment)
                        })
            
            elif analysis_type == 'cracked':
                if 'cracking_analysis' in results:
                    cracking = results['cracking_analysis']
                    summary['key_findings'][analysis_type].append({
                        'cracking_moment_kNm': float(cracking.m_cr / 1e6),
                        'neutral_axis_depth_mm': float(cracking.d_nc)
                    })
                
                for key, stress_res in results.items():
                    if key != 'cracking_analysis' and hasattr(stress_res, 'get_concrete_stress_limits'):
                        min_stress, max_stress = stress_res.get_concrete_stress_limits()
                        net_force = stress_res.sum_forces()
                        net_moment = stress_res.sum_moments()[2]
                        
                        # Count tension bars
                        tension_bars = 0
                        if hasattr(stress_res, 'lumped_reinforcement_stresses'):
                            for stress in stress_res.lumped_reinforcement_stresses:
                                if stress < 0:  # Tension stress
                                    tension_bars += 1
                        
                        summary['key_findings'][analysis_type].append({
                            'case': key,
                            'concrete_min_stress_MPa': float(min_stress),
                            'concrete_max_stress_MPa': float(max_stress),
                            'net_force_N': float(net_force),
                            'net_moment_Nmm': float(net_moment),
                            'tension_bars_count': tension_bars
                        })
            
            elif analysis_type == 'service':
                if 'moment_curvature' in results:
                    mk_res = results['moment_curvature']
                    summary['key_findings'][analysis_type].append({
                        'ultimate_moment_kNm': float(mk_res.m_xy[-1] / 1e6),
                        'ultimate_curvature': float(mk_res.kappa[-1]),
                        'num_points': len(mk_res.kappa)
                    })
                
                for key, stress_res in results.items():
                    if key != 'moment_curvature' and hasattr(stress_res, 'get_concrete_stress_limits'):
                        min_stress, max_stress = stress_res.get_concrete_stress_limits()
                        
                        summary['key_findings'][analysis_type].append({
                            'case': key,
                            'concrete_min_stress_MPa': float(min_stress),
                            'concrete_max_stress_MPa': float(max_stress)
                        })
            
            elif analysis_type == 'ultimate':
                if 'moment_interaction' in results:
                    mi_res = results['moment_interaction']
                    mi_res.sort_results()
                    summary['key_findings'][analysis_type].append({
                        'max_compression_kN': float(mi_res.results[0].n / 1e3),
                        'pure_bending_kNm': float(mi_res.results[-1].m_xy / 1e6)
                    })
                
                for key, result_dict in results.items():
                    if key != 'moment_interaction' and 'stress_results' in result_dict:
                        stress_res = result_dict['stress_results']
                        ultimate_res = result_dict['ultimate_results']
                        min_stress, max_stress = stress_res.get_concrete_stress_limits()
                        
                        summary['key_findings'][analysis_type].append({
                            'case': key,
                            'axial_force_kN': float(ultimate_res.n / 1e3),
                            'moment_kNm': float(ultimate_res.m_xy / 1e6),
                            'neutral_axis_mm': float(ultimate_res.d_n),
                            'concrete_max_stress_MPa': float(max_stress)
                        })
        
        # Save summary
        filename = "60_stress_analysis_summary.json"
        json_path = os.path.join(output_dir, filename)
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ Stress analysis summary saved: {filename}")
        
        # Print key insights
        print("\nKEY STRESS ANALYSIS INSIGHTS:")
        
        if 'cracked' in summary['key_findings']:
            for finding in summary['key_findings']['cracked']:
                if 'cracking_moment_kNm' in finding:
                    print(f"  • Cracking moment: {finding['cracking_moment_kNm']:.1f} kN·m")
        
        if 'ultimate' in summary['key_findings']:
            for finding in summary['key_findings']['ultimate']:
                if 'max_compression_kN' in finding:
                    print(f"  • Maximum compression capacity: {finding['max_compression_kN']:.0f} kN")
                if 'pure_bending_kNm' in finding:
                    print(f"  • Pure bending capacity: {finding['pure_bending_kNm']:.0f} kN·m")
        
        return json_path


def create_concrete_section_example():
    """Create a ConcreteSection using sectionproperties geometry with concreteproperties materials."""
    
    # Define concreteproperties materials
    concrete = Concrete(
        name="40 MPa Concrete",
        density=2400e-9,
        stress_strain_profile=ssp.ConcreteLinear(elastic_modulus=32.8e3),
        ultimate_stress_strain_profile=ssp.RectangularStressBlock(
            compressive_strength=40,
            alpha=0.79,
            gamma=0.87,
            ultimate_strain=0.003,
        ),
        flexural_tensile_strength=3.8,
        colour="lightgrey",
    )
    
    steel = SteelBar(
        name="500 MPa Steel",
        density=7850e-9,
        stress_strain_profile=ssp.SteelElasticPlastic(
            yield_strength=500,
            elastic_modulus=200e3,
            fracture_strain=0.05,
        ),
        colour="darkred",
    )
    
    # Create geometry using sectionproperties library
    web = rectangular_section(d=600, b=300, material=concrete)
    flange = rectangular_section(d=150, b=400, material=concrete).shift_section(
        x_offset=-50, y_offset=600
    )
    geom = web + flange
    
    # Add bottom reinforcement (tension zone) - add to geometry BEFORE creating ConcreteSection
    bottom_rebars = [(50, 50), (150, 50), (250, 50)]
    for x, y in bottom_rebars:
        geom = add_bar(
            geometry=geom,
            area=np.pi * 12.5**2,
            material=steel,
            x=x,
            y=y,
            n=12
        )
    
    # Add top reinforcement (compression zone)
    top_rebars = [(50, 550), (250, 550)]
    for x, y in top_rebars:
        geom = add_bar(
            geometry=geom,
            area=np.pi * 10**2,
            material=steel,
            x=x,
            y=y,
            n=12
        )
    
    # Create ConcreteSection - it handles meshing automatically
    conc_sec = ConcreteSection(geom)
    
    return conc_sec, concrete, steel


if __name__ == "__main__":
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    builder = CompositeSectionBuilder()
    
    print("Creating concrete section...")
    conc_sec, concrete_mat, steel_mat = create_concrete_section_example()
    
    print("\nSaving gross properties...")
    builder.save_gross_properties(conc_sec, output_dir)
    
    print("\nSaving transformed gross properties...")
    E_ref = 32.8e3
    builder.save_transformed_gross_properties(conc_sec, E_ref, output_dir)
    
    print("\nSaving cracked properties...")
    builder.save_cracked_properties_sagging(conc_sec, output_dir)
    builder.save_cracked_properties_hogging(conc_sec, output_dir)
    
    print("\nSaving transformed cracked properties...")
    builder.save_transformed_cracked_properties_sagging(conc_sec, E_ref, output_dir)
    builder.save_transformed_cracked_properties_hogging(conc_sec, E_ref, output_dir)
    
    print("\nSaving specific cracked results...")
    builder.save_specific_cracked_results(conc_sec, output_dir)
    
    print("\nPlotting cracked geometries...")
    builder.plot_cracked_geometries(conc_sec, output_dir)
    
    print("\nPlotting material stress-strain profiles...")
    builder.plot_stress_strain_profiles([concrete_mat], [steel_mat], output_dir)
    
    print("\nPerforming comprehensive moment-curvature analysis...")
    mc_results = builder.analyze_with_varying_parameters(conc_sec, output_dir)
    print("\nPerforming ultimate bending capacity analysis...")
    ub_results = builder.analyze_ultimate_bending_capacities(conc_sec, output_dir)
    
    # Create comparison plot
    builder.plot_ultimate_bending_comparison(ub_results, output_dir)

    print("\nPerforming moment interaction analysis...")
    mi_results = builder.analyze_moment_interaction(conc_sec, output_dir)

    print("\nPerforming biaxial bending analysis...")
    bb_results = builder.analyze_biaxial_bending(conc_sec, output_dir)
    
    # Example: Check a biaxial design point
    print("\nChecking biaxial design point example...")
    biaxial_check = builder.check_biaxial_design_point(
        bb_results['comp1'],  # N=1000 kN case
        m_x_design=1500e6,    # 1500 kN·m about x-axis
        m_y_design=800e6      # 800 kN·m about y-axis
    )
    
    if biaxial_check['within_capacity']:
        print(f"✓ Biaxial design point is within capacity")
    else:
        print(f"✗ Biaxial design point exceeds capacity")
        closest = biaxial_check['closest_point']
        print(f"  Closest point: M_x={closest['m_x_kNm']:.1f} kN·m, "
              f"M_y={closest['m_y_kNm']:.1f} kN·m")
        
        if biaxial_check['interaction_ratio']:
            print(f"  Interaction ratio: {biaxial_check['interaction_ratio']:.2f} "
                  f"(>1.0 indicates failure)")
    
    print("\nPerforming comprehensive stress analysis...")
    stress_results = builder.perform_stress_analysis(conc_sec, output_dir)
    
    print(f"\n✅ All analysis files created successfully in: {output_dir}")
    print("\nGenerated files:")
    print(" 1-9. Section properties and cracked analysis")
    print("10-17. Moment-curvature analysis")
    print("13-14. Material stress-strain profiles")
    print("18-26. Ultimate bending capacity analysis")
    print("27-34. Moment interaction diagram analysis")
    print("35-44. Biaxial bending diagram analysis")
    print("45-60. Stress analysis (all types)")
