import matplotlib.pyplot as plt
import numpy as np

# Set a professional style for the plots
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10


def generate_kinematic_features_plot():
    """
    Generates and saves the Barbell Trajectory and Knee Angle Over Time graphs.
    This simulates the data shown in Figure 18.
    """
    # --- Data Generation for Kinematic Plots ---
    
    # 1. Barbell Trajectory Data (S-shaped curve for a snatch/clean)
    y_barbell = np.linspace(0, 1, 50)  # Vertical position (normalized)
    # Simulate the bar moving back towards the lifter then up and slightly forward
    x_barbell = 0.5 - 0.04 * np.sin(y_barbell * np.pi * 1.5) 
    
    # 2. Knee Angle Data (starts bent, extends, then bends again for the catch)
    time = np.linspace(0, 3, 100)
    # Use a sine wave to simulate the angle change: 90 -> 110 -> 90 degrees
    knee_angle = 90 + 20 * np.sin(np.linspace(0, np.pi, 100))
    
    # --- Plotting ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Plot 1: Barbell Trajectory
    ax1.plot(x_barbell, y_barbell, 'o-', color='darkblue', markersize=4, label='Barbell Path')
    ax1.set_title('Barbell Trajectory', fontweight='bold')
    ax1.set_xlabel('Horizontal Position (normalized units)')
    ax1.set_ylabel('Vertical Position (normalized units)')
    ax1.set_xlim(0.45, 0.55)
    ax1.set_ylim(0, 1.05)
    
    # Plot 2: Knee Angle Over Time
    ax2.plot(time, knee_angle, color='green', linewidth=2, label='Knee Angle')
    ax2.set_title('Knee Angle Over Time', fontweight='bold')
    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('Angle (degrees)')
    ax2.set_ylim(88, 112)

    fig.suptitle('Figure 18: Extracted Kinematic Features', fontsize=16, y=1.02)
    fig.tight_layout()
    
    # Save the figure
    plt.savefig('figure_18_kinematic_features.png', dpi=300, bbox_inches='tight')
    print("Generated 'figure_18_kinematic_features.png'")


def generate_fault_detection_metrics_plot():
    """
    Generates a grouped bar chart for the AI fault detection performance metrics.
    This visualizes the data from Table II.
    """
    faults = ['Early Arm Bend', 'Incomplete Hip\nExtension', 'Bar Forward\nin Catch']
    metrics = {
        'Precision': [0.94, 0.86, 0.89],
        'Recall': [0.90, 0.84, 0.87],
        'F1-Score': [0.92, 0.85, 0.88],
    }

    x = np.arange(len(faults))  # the label locations
    width = 0.25  # the width of the bars
    multiplier = 0

    fig, ax = plt.subplots(figsize=(10, 6))

    for attribute, measurement in metrics.items():
        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute)
        ax.bar_label(rects, padding=3, fmt='%.2f')
        multiplier += 1

    # Add some text for labels, title and axes ticks
    ax.set_ylabel('Score')
    ax.set_title('Table II: AI Fault Detection Performance Metrics', fontweight='bold', pad=20)
    ax.set_xticks(x + width, faults)
    ax.legend(loc='upper left', ncols=3)
    ax.set_ylim(0, 1.1)

    fig.tight_layout()
    
    # Save the figure
    plt.savefig('table_2_fault_detection_metrics.png', dpi=300, bbox_inches='tight')
    print("Generated 'table_2_fault_detection_metrics.png'")


def generate_sus_scores_plot():
    """
    Generates a bar chart for the System Usability Scale (SUS) scores.
    This visualizes the data from Table III.
    """
    groups = ['Weightlifters', 'Coaches', 'Overall']
    scores = [81.0, 84.5, 82.5]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    bars = ax.bar(groups, scores, color=['#1f77b4', '#2ca02c', '#9467bd'])
    
    # Add the benchmark line for "Acceptable Usability"
    ax.axhline(y=68, color='red', linestyle='--', linewidth=2, label='Acceptable Usability Benchmark (68)')
    
    ax.bar_label(bars, fmt='%.1f', padding=3, fontsize=12)
    
    ax.set_ylabel('Average SUS Score')
    ax.set_title('Table III: System Usability Scale (SUS) Scores', fontweight='bold', pad=20)
    ax.set_ylim(0, 100)
    ax.legend()
    
    fig.tight_layout()

    # Save the figure
    plt.savefig('table_3_sus_scores.png', dpi=300, bbox_inches='tight')
    print("Generated 'table_3_sus_scores.png'")

def generate_pose_estimation_plot():
    """
    Generates a mock visualization for the pose estimation validation figure.
    This simulates Figure 17.
    Note: This does not use a real image or a real pose estimation model.
    It creates a plot with skeletal keypoints to represent the concept.
    """
    # Keypoints for a squat position (x, y) - normalized coordinates
    keypoints = {
        'nose': (0.5, 0.9), 'left_shoulder': (0.4, 0.8), 'right_shoulder': (0.6, 0.8),
        'left_elbow': (0.35, 0.7), 'right_elbow': (0.65, 0.7), 'left_wrist': (0.3, 0.9), 'right_wrist': (0.7, 0.9),
        'left_hip': (0.45, 0.6), 'right_hip': (0.55, 0.6), 'left_knee': (0.4, 0.4), 'right_knee': (0.6, 0.4),
        'left_ankle': (0.4, 0.2), 'right_ankle': (0.6, 0.2)
    }
    
    # Connections between keypoints
    skeleton = [
        ('left_shoulder', 'right_shoulder'), ('left_hip', 'right_hip'),
        ('left_shoulder', 'left_elbow'), ('left_elbow', 'left_wrist'),
        ('right_shoulder', 'right_elbow'), ('right_elbow', 'right_wrist'),
        ('left_shoulder', 'left_hip'), ('right_shoulder', 'right_hip'),
        ('left_hip', 'left_knee'), ('left_knee', 'left_ankle'),
        ('right_hip', 'right_knee'), ('right_knee', 'right_ankle')
    ]
    
    fig, ax = plt.subplots(figsize=(6, 8))

    # Plot the skeleton lines
    for start_kp, end_kp in skeleton:
        x_coords = [keypoints[start_kp][0], keypoints[end_kp][0]]
        y_coords = [keypoints[start_kp][1], keypoints[end_kp][1]]
        ax.plot(x_coords, y_coords, color='green', linewidth=3)
        
    # Plot the keypoints
    for kp, (x, y) in keypoints.items():
        ax.plot(x, y, 'o', color='red', markersize=8)

    ax.set_title('Figure 17: Pose Estimation Validation', fontweight='bold', pad=20)
    
    # Clean up the axes to look like an image overlay
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off') # Hide axes

    plt.savefig('figure_17_pose_estimation.png', dpi=300, bbox_inches='tight')
    print("Generated 'figure_17_pose_estimation.png'")


if __name__ == '__main__':
    print("Generating graphs for LiftCoach AI Thesis...")
    generate_kinematic_features_plot()
    generate_fault_detection_metrics_plot()
    generate_sus_scores_plot()
    generate_pose_estimation_plot() # Note: This is a schematic, not a real image overlay
    print("\nAll graphs have been generated and saved as PNG files.")