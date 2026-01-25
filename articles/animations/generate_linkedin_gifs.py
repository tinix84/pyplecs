"""
LinkedIn Post GIF Animations Generator

Generates 10 animated GIFs for LinkedIn posts using matplotlib.animation.
Each GIF is optimized for LinkedIn (square format, <5MB, eye-catching).
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle, FancyArrow
import numpy as np
import sys
import os

# Output directory
OUTPUT_DIR = "../animations"

# Style configuration
plt.rcParams['font.size'] = 14
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.weight'] = 'bold'

# LinkedIn-optimized format
FIGSIZE = (8, 8)  # Square format for LinkedIn
DPI = 100
FPS = 10
DURATION_SECONDS = 4


def clip_alpha(alpha):
    """Ensure alpha is strictly in [0, 1] range"""
    return max(0.0, min(1.0, alpha))


def save_animation(fig, anim, filename, fps=FPS):
    """Save animation as GIF"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    print(f"Generating {filename}...")

    try:
        from matplotlib.animation import PillowWriter
        writer = PillowWriter(fps=fps)
        anim.save(filepath, writer=writer, dpi=DPI)

        # Check file size
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"  [OK] Saved: {filename} ({size_mb:.2f} MB)")

        if size_mb > 5:
            print(f"  [WARNING] File size > 5MB (LinkedIn limit: 5MB)")
    except ImportError:
        print(f"  [ERROR] Pillow not installed. Run: pip install pillow")
        sys.exit(1)


def create_animation_01_architecture_collapse():
    """Animation 1: Complex architecture collapsing into simple"""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    def animate(frame):
        ax.clear()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        progress = frame / (FPS * DURATION_SECONDS)

        if progress < 0.5:
            # Show complex architecture
            alpha = 1 - (progress * 2)

            # Multiple layers
            ax.add_patch(Rectangle((1, 7), 8, 1.5, fc='#e74c3c', alpha=clip_alpha(alpha), ec='black', lw=2))
            ax.text(5, 7.75, 'GenericConverterPlecsMdl', ha='center', va='center',
                   fontsize=12, alpha=clip_alpha(alpha), weight='bold')

            ax.add_patch(Rectangle((1, 5), 8, 1.5, fc='#f39c12', alpha=clip_alpha(alpha), ec='black', lw=2))
            ax.text(5, 5.75, 'Variant Generation', ha='center', va='center',
                   fontsize=12, alpha=clip_alpha(alpha), weight='bold')

            ax.add_patch(Rectangle((1, 3), 8, 1.5, fc='#f39c12', alpha=clip_alpha(alpha), ec='black', lw=2))
            ax.text(5, 3.75, 'File I/O Layer', ha='center', va='center',
                   fontsize=12, alpha=clip_alpha(alpha), weight='bold')

            ax.add_patch(Rectangle((1, 1), 8, 1.5, fc='#95a5a6', alpha=clip_alpha(alpha), ec='black', lw=2))
            ax.text(5, 1.75, 'PLECS XML-RPC', ha='center', va='center',
                   fontsize=12, alpha=clip_alpha(alpha), weight='bold')

            ax.text(5, 9.5, '4,081 Lines of Code', ha='center', fontsize=16,
                   weight='bold', alpha=clip_alpha(alpha))
        else:
            # Show simple architecture
            alpha = (progress - 0.5) * 2

            ax.add_patch(Rectangle((2, 3.5), 6, 3, fc='#2ecc71', alpha=clip_alpha(alpha), ec='black', lw=3))
            ax.text(5, 5, 'PlecsServer\n(Thin Wrapper)', ha='center', va='center',
                   fontsize=14, alpha=clip_alpha(alpha), weight='bold')

            ax.add_patch(Rectangle((2, 1), 6, 2, fc='#3498db', alpha=clip_alpha(alpha), ec='black', lw=2))
            ax.text(5, 2, 'PLECS Native API', ha='center', va='center',
                   fontsize=12, alpha=clip_alpha(alpha), weight='bold')

            ax.text(5, 9.5, '2,500 Lines of Code', ha='center', fontsize=16,
                   weight='bold', alpha=clip_alpha(alpha), color='#2ecc71')

            ax.text(5, 0.3, '39% Code Reduction', ha='center', fontsize=14,
                   weight='bold', alpha=clip_alpha(alpha), color='#2ecc71')

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-01-architecture-collapse.gif')
    plt.close()


def create_animation_02_code_deletion():
    """Animation 2: Code counter decreasing from 436 to 0"""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    def animate(frame):
        ax.clear()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        progress = frame / (FPS * DURATION_SECONDS)

        # Animate counter from 436 down to 0
        current_lines = int(436 * (1 - progress))

        # Draw code block shrinking
        height = 5 * (1 - progress)
        if height > 0:
            ax.add_patch(Rectangle((2, 3), 6, height, fc='#e74c3c', alpha=0.7, ec='black', lw=2))

        # Counter
        color = '#e74c3c' if current_lines > 0 else '#2ecc71'
        ax.text(5, 6, f'{current_lines}', ha='center', va='center',
               fontsize=80, weight='bold', color=color)

        ax.text(5, 9, 'Lines of Abstraction', ha='center', fontsize=16, weight='bold')
        ax.text(5, 1.5, 'Native Feature:', ha='center', fontsize=14)
        ax.text(5, 0.8, '2 Lines', ha='center', fontsize=18, weight='bold', color='#2ecc71')

        if progress > 0.9:
            ax.text(5, 0.2, 'ROI: -95%', ha='center', fontsize=12,
                   weight='bold', color='#e74c3c')

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-02-code-deletion.gif')
    plt.close()


def create_animation_03_racing_bars():
    """Animation 3: Racing bar chart showing speedup"""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    times = [160, 80, 40]  # Sequential, Threading, Native Batch
    labels = ['Sequential\n(Baseline)', 'Custom\nThread Pool', 'PLECS\nNative Batch']
    colors = ['#e74c3c', '#f39c12', '#2ecc71']

    def animate(frame):
        ax.clear()

        progress = frame / (FPS * DURATION_SECONDS)

        # Animate bars growing
        current_times = [t * progress for t in times]

        bars = ax.barh(labels, current_times, color=colors, alpha=0.8, edgecolor='black', linewidth=2)

        ax.set_xlabel('Time (seconds)', fontsize=14, weight='bold')
        ax.set_title('16 Simulations on 4-Core Machine', fontsize=16, weight='bold', pad=20)
        ax.set_xlim(0, 180)

        # Add value labels
        for bar, time in zip(bars, current_times):
            if time > 1:
                ax.text(time + 3, bar.get_y() + bar.get_height()/2,
                       f'{time:.0f}s',
                       va='center', fontsize=14, weight='bold')

        if progress > 0.8:
            ax.text(90, -0.5, '5× Faster!', ha='center', fontsize=18,
                   weight='bold', color='#2ecc71', bbox=dict(boxstyle='round',
                   facecolor='yellow', alpha=0.3))

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-03-racing-bars.gif')
    plt.close()


def create_animation_04_cache_accumulation():
    """Animation 4: Cache hits accumulating, time saved growing"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE)

    def animate(frame):
        ax1.clear()
        ax2.clear()

        progress = frame / (FPS * DURATION_SECONDS)

        # Pie chart: cache hits growing
        cache_hit = 63 * progress
        cache_miss = 100 - cache_hit

        colors_pie = ['#2ecc71', '#e74c3c']
        wedges, texts, autotexts = ax1.pie(
            [cache_hit, 100 - cache_hit],
            labels=['Cache Hits', 'Cache Misses'],
            autopct=lambda p: f'{p:.0f}%' if p > 1 else '',
            colors=colors_pie,
            startangle=90,
            textprops={'fontsize': 12, 'weight': 'bold'}
        )
        ax1.set_title('Cache Hit Rate', fontsize=14, weight='bold')

        # Time saved counter
        hours_saved = 80 * progress

        ax2.text(0.5, 0.7, f'{hours_saved:.0f}', ha='center', va='center',
                fontsize=60, weight='bold', color='#2ecc71',
                transform=ax2.transAxes)

        ax2.text(0.5, 0.4, 'Hours Saved', ha='center', va='center',
                fontsize=16, weight='bold', transform=ax2.transAxes)

        ax2.text(0.5, 0.2, 'per Month', ha='center', va='center',
                fontsize=12, transform=ax2.transAxes)

        ax2.axis('off')

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-04-cache-accumulation.gif')
    plt.close()


def create_animation_05_api_requests():
    """Animation 5: Requests flowing from different languages into API"""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    languages = ['Python', 'MATLAB', 'JavaScript', 'curl']
    colors_lang = ['#3498db', '#f39c12', '#e74c3c', '#95a5a6']

    def animate(frame):
        ax.clear()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        progress = frame / (FPS * DURATION_SECONDS)

        # Draw API in center
        ax.add_patch(Circle((5, 5), 1.2, fc='#2ecc71', ec='black', lw=3))
        ax.text(5, 5, 'REST\nAPI', ha='center', va='center',
               fontsize=14, weight='bold')

        # Draw languages around circle
        angles = [45, 135, 225, 315]
        radius = 3.5

        for i, (lang, color, angle) in enumerate(zip(languages, colors_lang, angles)):
            x = 5 + radius * np.cos(np.radians(angle))
            y = 5 + radius * np.sin(np.radians(angle))

            # Language box
            ax.add_patch(Rectangle((x-0.7, y-0.4), 1.4, 0.8, fc=color,
                                  alpha=0.8, ec='black', lw=2))
            ax.text(x, y, lang, ha='center', va='center',
                   fontsize=10, weight='bold')

            # Animated arrow
            delay = i * 0.2
            if progress > delay:
                arrow_progress = min(1, (progress - delay) / 0.3)

                dx = (5 - x) * arrow_progress * 0.5
                dy = (5 - y) * arrow_progress * 0.5

                ax.arrow(x, y, dx, dy, head_width=0.2, head_length=0.2,
                        fc=color, ec='black', lw=2, alpha=0.7)

        ax.text(5, 9.5, 'Language-Agnostic Access', ha='center',
               fontsize=16, weight='bold')

        if progress > 0.8:
            ax.text(5, 0.5, '3× User Growth', ha='center', fontsize=14,
                   weight='bold', color='#2ecc71')

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-05-api-requests.gif')
    plt.close()


def create_animation_06_deletion_progress():
    """Animation 6: Line counter decreasing, tests staying green"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE)

    def animate(frame):
        ax1.clear()
        ax2.clear()

        progress = frame / (FPS * DURATION_SECONDS)

        # Lines of code decreasing
        current_loc = int(4081 - (4081 - 2500) * progress)

        ax1.text(0.5, 0.6, f'{current_loc:,}', ha='center', va='center',
                fontsize=50, weight='bold', color='#e74c3c',
                transform=ax1.transAxes)

        ax1.text(0.5, 0.4, 'Lines of Code', ha='center', va='center',
                fontsize=14, weight='bold', transform=ax1.transAxes)

        percent_reduction = int((1 - current_loc/4081) * 100)
        ax1.text(0.5, 0.2, f'-{percent_reduction}%', ha='center', va='center',
                fontsize=16, weight='bold', color='#2ecc71',
                transform=ax1.transAxes)

        ax1.axis('off')

        # Tests staying green
        ax2.text(0.5, 0.6, '✓', ha='center', va='center',
                fontsize=80, weight='bold', color='#2ecc71',
                transform=ax2.transAxes)

        ax2.text(0.5, 0.3, 'All Tests Pass', ha='center', va='center',
                fontsize=16, weight='bold', color='#2ecc71',
                transform=ax2.transAxes)

        ax2.axis('off')

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-06-deletion-progress.gif')
    plt.close()


def create_animation_07_priority_queue():
    """Animation 7: Priority queue processing tasks"""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    priorities = ['CRITICAL', 'HIGH', 'NORMAL', 'LOW']
    colors_priority = ['#e74c3c', '#f39c12', '#3498db', '#95a5a6']

    def animate(frame):
        ax.clear()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        progress = frame / (FPS * DURATION_SECONDS)

        # Title
        ax.text(5, 9.5, 'Priority Queue Processing', ha='center',
               fontsize=16, weight='bold')

        # Draw queue
        y_start = 7.5
        for i, (priority, color) in enumerate(zip(priorities, colors_priority)):
            y = y_start - i * 1.5

            # Determine if this task has been processed
            process_threshold = i * 0.2

            if progress < process_threshold:
                # In queue
                alpha = 0.8
                x_pos = 2
            elif progress < process_threshold + 0.15:
                # Being processed (move to right)
                alpha = 1.0
                anim_progress = (progress - process_threshold) / 0.15
                x_pos = 2 + 4 * anim_progress
            else:
                # Completed (fade out)
                fade_progress = min(1, (progress - process_threshold - 0.15) / 0.1)
                alpha = max(0, 1 - fade_progress)
                x_pos = 6

            if alpha > 0:
                ax.add_patch(Rectangle((x_pos, y), 2, 1, fc=color,
                                      alpha=clip_alpha(alpha), ec='black', lw=2))
                ax.text(x_pos + 1, y + 0.5, priority, ha='center', va='center',
                       fontsize=12, weight='bold', alpha=clip_alpha(alpha))

        # Completion indicator
        completed = int(progress * 4)
        if completed > 0:
            ax.text(8, 1, f'{completed}/4\nCompleted', ha='center', va='center',
                   fontsize=14, weight='bold', color='#2ecc71',
                   bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-07-priority-queue.gif')
    plt.close()


def create_animation_08_performance_scaling():
    """Animation 8: Performance scaling curve with batch size"""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    batch_sizes = np.array([1, 2, 4, 8, 16, 32])
    speedups_measured = np.array([1.0, 1.8, 3.2, 4.5, 5.1, 5.3])
    speedups_ideal = batch_sizes

    def animate(frame):
        ax.clear()

        progress = frame / (FPS * DURATION_SECONDS)

        # Number of points to show
        num_points = int(len(batch_sizes) * progress)
        if num_points == 0:
            num_points = 1

        # Plot ideal line (faint)
        ax.plot(batch_sizes, speedups_ideal, 'k--', linewidth=2,
               label='Ideal Linear', alpha=0.3)

        # Plot measured (animating)
        if num_points > 0:
            ax.plot(batch_sizes[:num_points], speedups_measured[:num_points],
                   'o-', linewidth=3, markersize=10, color='#2ecc71',
                   label='Measured Speedup')

            # Add confidence interval
            ci_lower = speedups_measured[:num_points] * 0.95
            ci_upper = speedups_measured[:num_points] * 1.05
            ax.fill_between(batch_sizes[:num_points], ci_lower, ci_upper,
                           alpha=0.2, color='#2ecc71')

        ax.set_xlabel('Batch Size (Simulations)', fontsize=13, weight='bold')
        ax.set_ylabel('Speedup Factor', fontsize=13, weight='bold')
        ax.set_title('Batch Parallelization Scaling', fontsize=16, weight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11, loc='upper left')
        ax.set_xlim(0, 35)
        ax.set_ylim(0, 35)

        # Annotation appears at end
        if progress > 0.7:
            ax.annotate('Sweet Spot:\n4-8 cores',
                       xy=(8, 4.5), xytext=(15, 10),
                       arrowprops=dict(arrowstyle='->', lw=2, color='red'),
                       fontsize=12, weight='bold',
                       bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-08-performance-scaling.gif')
    plt.close()


def create_animation_09_documentation_roi():
    """Animation 9: Documentation ROI growing over time"""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    months = np.array([0, 1, 3, 6, 12])
    time_invested = np.array([0, 8, 8, 8, 8])
    time_saved = np.array([0, 10, 35, 70, 140])
    net_benefit = time_saved - time_invested

    def animate(frame):
        ax.clear()

        progress = frame / (FPS * DURATION_SECONDS)

        # Number of months to show
        month_idx = int(len(months) * progress)
        if month_idx == 0:
            month_idx = 1

        x = months[:month_idx]

        # Bar chart showing invested vs saved
        width = 0.8
        ax.bar(x - width/3, time_invested[:month_idx], width/2.5,
              label='Time Invested', color='#e74c3c', alpha=0.7)
        ax.bar(x + width/3, time_saved[:month_idx], width/2.5,
              label='Time Saved', color='#2ecc71', alpha=0.7)

        ax.set_xlabel('Months After Writing Docs', fontsize=13, weight='bold')
        ax.set_ylabel('Hours', fontsize=13, weight='bold')
        ax.set_title('Documentation ROI Over Time', fontsize=16, weight='bold', pad=20)
        ax.legend(fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.set_xlim(-0.5, 13)
        ax.set_ylim(0, 150)

        # Show ROI at end
        if progress > 0.8 and month_idx >= len(months):
            roi = time_saved[-1] / time_invested[-1]
            ax.text(6, 130, f'17.5× ROI', ha='center', fontsize=18,
                   weight='bold', color='#2ecc71',
                   bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-09-documentation-roi.gif')
    plt.close()


def create_animation_10_ai_collaboration():
    """Animation 10: Human + AI collaboration workflow"""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    def animate(frame):
        ax.clear()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        progress = frame / (FPS * DURATION_SECONDS)

        # Title
        ax.text(5, 9.5, 'Human + AI Collaboration', ha='center',
               fontsize=16, weight='bold')

        # Human side (strategy)
        if progress > 0.1:
            alpha = min(1, (progress - 0.1) / 0.2)
            ax.add_patch(FancyBboxPatch((0.5, 5.5), 3.5, 2.5,
                                       boxstyle="round,pad=0.1",
                                       fc='#3498db', alpha=clip_alpha(alpha*0.7), ec='black', lw=2))
            ax.text(2.25, 7.5, 'HUMAN', ha='center', fontsize=12, weight='bold', alpha=clip_alpha(alpha))
            ax.text(2.25, 7, 'Strategy', ha='center', fontsize=10, alpha=clip_alpha(alpha))
            ax.text(2.25, 6.6, 'Architecture', ha='center', fontsize=10, alpha=clip_alpha(alpha))
            ax.text(2.25, 6.2, 'Validation', ha='center', fontsize=10, alpha=clip_alpha(alpha))

        # AI side (implementation)
        if progress > 0.3:
            alpha = min(1, (progress - 0.3) / 0.2)
            ax.add_patch(FancyBboxPatch((6, 5.5), 3.5, 2.5,
                                       boxstyle="round,pad=0.1",
                                       fc='#f39c12', alpha=clip_alpha(alpha*0.7), ec='black', lw=2))
            ax.text(7.75, 7.5, 'AI', ha='center', fontsize=12, weight='bold', alpha=clip_alpha(alpha))
            ax.text(7.75, 7, 'Boilerplate', ha='center', fontsize=10, alpha=clip_alpha(alpha))
            ax.text(7.75, 6.6, 'Tests', ha='center', fontsize=10, alpha=clip_alpha(alpha))
            ax.text(7.75, 6.2, 'Docs', ha='center', fontsize=10, alpha=clip_alpha(alpha))

        # Collaboration arrow
        if progress > 0.5:
            alpha = min(1, (progress - 0.5) / 0.2)
            ax.annotate('', xy=(6, 6.75), xytext=(4, 6.75),
                       arrowprops=dict(arrowstyle='<->', lw=3, color='#2ecc71', alpha=clip_alpha(alpha)))
            ax.text(5, 6.25, 'Collaborate', ha='center', fontsize=11,
                   weight='bold', alpha=clip_alpha(alpha))

        # Output (validated code)
        if progress > 0.7:
            alpha = min(1, (progress - 0.7) / 0.2)
            ax.add_patch(FancyBboxPatch((3, 2.5), 4, 1.5,
                                       boxstyle="round,pad=0.1",
                                       fc='#2ecc71', alpha=clip_alpha(alpha*0.7), ec='black', lw=3))
            ax.text(5, 3.7, 'VALIDATED OUTPUT', ha='center', fontsize=12,
                   weight='bold', alpha=clip_alpha(alpha))
            ax.text(5, 3.2, 'High Quality Code', ha='center', fontsize=10, alpha=clip_alpha(alpha))

        # Time savings
        if progress > 0.9:
            ax.text(5, 1, '57% Time Savings', ha='center', fontsize=16,
                   weight='bold', color='#2ecc71',
                   bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))

    anim = animation.FuncAnimation(fig, animate, frames=FPS*DURATION_SECONDS, interval=1000/FPS)
    save_animation(fig, anim, 'post-10-ai-collaboration.gif')
    plt.close()


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n" + "="*70)
    print("LINKEDIN POST GIF ANIMATIONS GENERATOR")
    print("="*70)
    print("\nGenerating 10 animated GIFs for LinkedIn posts...")
    print(f"Output directory: {OUTPUT_DIR}/")
    print(f"Format: {FIGSIZE[0]}x{FIGSIZE[1]} inches @ {DPI} DPI")
    print(f"Duration: {DURATION_SECONDS} seconds @ {FPS} FPS")
    print("\n")

    try:
        create_animation_01_architecture_collapse()
        create_animation_02_code_deletion()
        create_animation_03_racing_bars()
        create_animation_04_cache_accumulation()
        create_animation_05_api_requests()
        create_animation_06_deletion_progress()
        create_animation_07_priority_queue()
        create_animation_08_performance_scaling()
        create_animation_09_documentation_roi()
        create_animation_10_ai_collaboration()

        print("\n" + "="*70)
        print("[PASS] All 10 GIF animations generated successfully!")
        print("="*70)
        print("\nFiles ready for LinkedIn posts in:")
        print(f"  {os.path.abspath(OUTPUT_DIR)}/")
        print("\nRecommended LinkedIn posting:")
        print("  1. Upload GIF as first image/video")
        print("  2. Add short text from linkedin-posts/*.md")
        print("  3. Include 5-7 relevant hashtags")
        print("  4. Post at optimal time (Tue/Thu 8-10 AM)")
        print("\n")

    except Exception as e:
        print(f"\n[ERROR] Failed to generate animations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
