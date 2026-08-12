# graph.py

import matplotlib.pyplot as plt
import numpy as np
import re
import os
import mplfinance as mpf
import pandas as pd

os.makedirs("replay-analysis", exist_ok=True)

def plot_player_speeds(df_telemetry, replay_date):
    """
    Identifies all players in the telemetry DataFrame, calculates their 
    3D velocity magnitudes, applies a smoothing window, and plots them as candlesticks.
    """
    # 1. Automatically find all unique player names from the column headers
    all_columns = df_telemetry.columns
    player_names = set()
    
    # Debug: Print available columns to help diagnose issues
    print(f"\n📊 Available columns: {all_columns.tolist()}")
    
    for col in all_columns:
        # Look for velocity columns - they indicate player data
        if "_vel_x" in col:
            # Extract player name by removing "_vel_x"
            player_name = col.replace("_vel_x", "")
            player_names.add(player_name)
            
    if not player_names:
        print("❌ No player velocity data found in the DataFrame.")
        print("   Expected columns like 'PlayerName_vel_x', 'PlayerName_vel_y', 'PlayerName_vel_z'")
        print(f"   Available columns: {all_columns.tolist()}")
        return
    
    print(f"✅ Found players: {sorted(player_names)}")
    
    # Check if 'time' column exists
    if "time" not in df_telemetry.columns:
        print("❌ 'time' column not found in DataFrame")
        return
    
    # Track if we successfully plot any players
    players_plotted = 0

    # 3. Loop through each player to compute their speed and create candlestick charts
    for player in sorted(player_names):
        try:
            # Try to get velocity columns for this player
            vel_x_col = f"{player}_vel_x"
            vel_y_col = f"{player}_vel_y"
            vel_z_col = f"{player}_vel_z"
            
            # Check if all required columns exist
            if vel_x_col not in df_telemetry.columns:
                print(f"⚠️ Missing column for player '{player}': {vel_x_col}")
                continue
            if vel_y_col not in df_telemetry.columns:
                print(f"⚠️ Missing column for player '{player}': {vel_y_col}")
                continue
            if vel_z_col not in df_telemetry.columns:
                print(f"⚠️ Missing column for player '{player}': {vel_z_col}")
                continue
            
            vel_x = df_telemetry[vel_x_col]
            vel_y = df_telemetry[vel_y_col]
            vel_z = df_telemetry[vel_z_col]
            
            # Calculate true 3D speed magnitude (Unreal Units per second)
            raw_speed = np.sqrt(vel_x**2 + vel_y**2 + vel_z**2)
            
            # Smooth out network tick noise using a 1-second rolling average window
            smoothed_speed = raw_speed.rolling(window=30, min_periods=1).mean()
            
            # Create DataFrame for candlestick chart
            speed_df = pd.DataFrame({
                'time': df_telemetry['time'],
                'speed': smoothed_speed
            })
            
            # Create a datetime index by converting seconds to timedelta
            # Starting from a reference date (e.g., today)
            base_date = pd.Timestamp.now().normalize()
            speed_df['datetime'] = base_date + pd.to_timedelta(speed_df['time'], unit='s')
            speed_df.set_index('datetime', inplace=True)
            
            # Resample to 2-second intervals for candlesticks
            ohlc_data = speed_df['speed'].resample('2s').ohlc()
            ohlc_data.dropna(inplace=True)
            
            if ohlc_data.empty:
                print(f"⚠️ Not enough data for candlestick chart for player '{player}'")
                continue
            
            # Create candlestick chart for this player
            fig, axes = mpf.plot(
                ohlc_data,
                type='candle',
                style='charles',
                volume=False,
                title=f'{replay_date}: {player} Speed Candlesticks',
                ylabel='Speed (Unreal Units / s)',
                ylabel_lower='',
                figsize=(14, 7),
                returnfig=True
            )
            
            # Add supersonic threshold lines
            axes[0].axhline(y=2200, color='red', linestyle='--', alpha=0.6, label="Supersonic Threshold (2200)")
            axes[0].axhline(y=2300, color='blue', linestyle='--', alpha=0.6, label="Max Speed (2300)")
            axes[0].legend(loc='upper right')
            
            # Save individual player chart
            plt.savefig(f"replay-analysis/{replay_date}_{player}_speed_candles.png", dpi=300)
            plt.close()
            
            players_plotted += 1
            print(f"✅ Candlestick chart saved for {player}")
            
        except Exception as e:
            print(f"⚠️ Error plotting player '{player}': {e}")
    
    if players_plotted == 0:
        print("❌ No players were successfully plotted. Check your DataFrame structure.")
        return
    
    print(f"✅ Generated candlestick charts for {players_plotted} players: {', '.join(sorted(player_names))}")

def plot_boost_usage(df, replay_date):
    """
    Plot boost usage for all players over time using candlesticks.
    """
    import matplotlib.pyplot as plt
    
    # Find all player boost columns
    boost_cols = [col for col in df.columns if col.endswith('_boost')]
    
    if not boost_cols:
        print("No boost data found in dataframe")
        return
    
    # Extract player names
    players = [col.replace('_boost', '') for col in boost_cols]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Candlestick chart for boost levels
    for player, col in zip(players, boost_cols):
        # Prepare data for candlestick
        boost_df = pd.DataFrame({
            'time': df['time'],
            'boost': df[col]
        })
        
        # Create a datetime index
        base_date = pd.Timestamp.now().normalize()
        boost_df['datetime'] = base_date + pd.to_timedelta(boost_df['time'], unit='s')
        boost_df.set_index('datetime', inplace=True)
        
        # Resample to 2-second intervals for candlesticks
        ohlc_boost = boost_df['boost'].resample('2s').ohlc()
        ohlc_boost.dropna(inplace=True)
        
        if ohlc_boost.empty:
            print(f"⚠️ Not enough data for boost candlestick for {player}")
            continue
        
        # Plot candlestick for each player
        fig_boost, axes = mpf.plot(
            ohlc_boost,
            type='candle',
            style='charles',
            volume=False,
            title=f'{replay_date}: {player} Boost Candlesticks',
            ylabel='Boost Percentage (%)',
            ylabel_lower='',
            figsize=(14, 7),
            returnfig=True
        )
        
        # Add reference lines
        axes[0].axhline(y=80, color='green', linestyle='--', alpha=0.5, label='High Boost (80%)')
        axes[0].axhline(y=20, color='red', linestyle='--', alpha=0.5, label='Low Boost (20%)')
        axes[0].legend(loc='upper right')
        
        # Save individual player boost chart
        plt.savefig(f"replay-analysis/{replay_date}_{player}_boost_candles.png", dpi=300)
        plt.close()
    
    # Also create line plots for comparison in the original style
    for player, col in zip(players, boost_cols):
        ax1.plot(df['time'], df[col], label=player, alpha=0.8, linewidth=1.5)
    
    ax1.set_xlabel('Match Time (Seconds)')
    ax1.set_ylabel('Boost Percentage (%)')
    ax1.set_title(f'{replay_date}: Boost Levels Over Time (Line View)', fontsize=14, fontweight=700)
    ax1.set_ylim(0, 105)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='upper right')
    ax1.axhline(y=80, color='green', linestyle='--', alpha=0.5, label='High Boost (80%)')
    ax1.axhline(y=20, color='red', linestyle='--', alpha=0.5, label='Low Boost (20%)')
    
    # Plot 2: Boost distribution histogram
    for player, col in zip(players, boost_cols):
        ax2.hist(df[col], bins=20, alpha=0.5, label=player, density=True)
    
    ax2.set_xlabel('Boost Percentage (%)')
    ax2.set_ylabel('Density')
    ax2.set_title(f'{replay_date}: Boost Distribution', fontsize=14, fontweight=700)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig(f"replay-analysis/{replay_date}_boost_usage.png", dpi=300)
    print(f"✅ Boost plots saved as '{replay_date}_boost_usage.png'")

# Alternative: Combined candlestick chart for all players
def plot_combined_candlesticks(df_telemetry, replay_date):
    """
    Creates a combined view with candlestick charts for all players.
    """
    all_columns = df_telemetry.columns
    player_names = set()
    
    for col in all_columns:
        if "_vel_x" in col:
            player_name = col.replace("_vel_x", "")
            player_names.add(player_name)
    
    if not player_names:
        print("❌ No player velocity data found in the DataFrame.")
        return
    
    # Create a figure with subplots for each player
    num_players = len(player_names)
    fig, axes = plt.subplots(num_players, 1, figsize=(14, 6*num_players))
    if num_players == 1:
        axes = [axes]
    
    for idx, player in enumerate(sorted(player_names)):
        try:
            vel_x = df_telemetry[f"{player}_vel_x"]
            vel_y = df_telemetry[f"{player}_vel_y"]
            vel_z = df_telemetry[f"{player}_vel_z"]
            
            raw_speed = np.sqrt(vel_x**2 + vel_y**2 + vel_z**2)
            smoothed_speed = raw_speed.rolling(window=30, min_periods=1).mean()
            
            # Prepare OHLC data with datetime index
            speed_df = pd.DataFrame({
                'time': df_telemetry['time'],
                'speed': smoothed_speed
            })
            
            base_date = pd.Timestamp.now().normalize()
            speed_df['datetime'] = base_date + pd.to_timedelta(speed_df['time'], unit='s')
            speed_df.set_index('datetime', inplace=True)
            
            # Resample to 2-second intervals
            ohlc_data = speed_df['speed'].resample('2s').ohlc()
            ohlc_data.dropna(inplace=True)
            
            if not ohlc_data.empty:
                # Use mplfinance to plot on the subplot
                mpf.plot(
                    ohlc_data,
                    type='candle',
                    style='charles',
                    volume=False,
                    title=f'{player} Speed Candlesticks',
                    ylabel='Speed (UU/s)',
                    figsize=(14, 4),
                    ax=axes[idx],
                    show_nontrading=False
                )
                
                axes[idx].axhline(y=2200, color='red', linestyle='--', alpha=0.6)
                axes[idx].axhline(y=2300, color='blue', linestyle='--', alpha=0.6)
                
        except Exception as e:
            print(f"⚠️ Error creating candlestick for {player}: {e}")
    
    plt.suptitle(f'{replay_date}: All Players Speed Candlesticks', fontsize=16, fontweight=700)
    plt.tight_layout()
    plt.savefig(f"replay-analysis/{replay_date}_all_players_candles.png", dpi=300)
    plt.close()
    print(f"✅ Combined candlestick chart saved for all players")


def calculate_advanced_boost_stats(df):
    """
    Calculate advanced boost statistics for each player.
    """
    stats = {}
    
    # Find all player boost columns
    boost_cols = [col for col in df.columns if col.endswith('_boost')]
    players = [col.replace('_boost', '') for col in boost_cols]
    
    for player, col in zip(players, boost_cols):
        boost_data = df[col]
        
        # Basic stats
        stats[player] = {
            'avg_boost': boost_data.mean(),
            'max_boost': boost_data.max(),
            'min_boost': boost_data.min(),
            'std_boost': boost_data.std(),
            
            # Time in boost zones
            'time_high_boost': (boost_data > 80).sum() / len(boost_data) * 100,
            'time_medium_boost': ((boost_data >= 40) & (boost_data <= 80)).sum() / len(boost_data) * 100,
            'time_low_boost': (boost_data < 40).sum() / len(boost_data) * 100,
            'time_empty_boost': (boost_data < 10).sum() / len(boost_data) * 100,
            
            # Boost efficiency
            'boost_usage_rate': boost_data.diff().abs().sum() / len(boost_data),
            'boost_avg_usage_per_second': boost_data.diff().abs().sum() / df['time'].max(),
            
            # Boost pad collection estimate (based on boost increases)
            'boost_increases': (boost_data.diff() > 0).sum(),
            'avg_increase_size': boost_data.diff()[boost_data.diff() > 0].mean() if (boost_data.diff() > 0).any() else 0,
        }
    
    return stats