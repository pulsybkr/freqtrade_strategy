import os
import concurrent.futures
import subprocess
import hashlib
import shlex
import re
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()

# Paths to directories
STRATEGY_PATH = "./user_data/strategies"
CONFIG_PATH = "./user_data/"
RESULTS_PATH = "./user_data/results"

# Available values for timeframe, timerange, spaces, and loss_functions
TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "1d"]
TIMERANGES = [
    "20240601-20240825", "20240701-20240825", "20240601-",
    "20240810-20240825", "20240820-20240825",
    "20240824-20240825", "20240725-20240825"
]
SPACES = [
    "roi stoploss", "roi stoploss trailing", "buy sell",
    "buy sell roi", "buy sell roi stoploss", "stoploss roi",
    "roi", "buy", "sell", "all"
]
LOSS_FUNCTIONS = [
    "ShortTradeDurHyperOptLoss", "OnlyProfitHyperOptLoss",
    "SharpeHyperOptLoss", "SortinoHyperOptLoss"
]

def get_choice(options, prompt, allow_custom=True):
    """
    Function for user to select an option or enter a custom value.
    """
    table = Table(show_header=False, border_style="blue")
    console.print(Panel(prompt, style="bold green"))
    
    for i, option in enumerate(options, start=1):
        table.add_row(f"[cyan]{i}.[/cyan] [yellow]{option}[/yellow]")
    
    if allow_custom:
        table.add_row(f"[cyan]{len(options) + 1}.[/cyan] [yellow]Enter your own value[/yellow]")
    
    console.print(table)

    while True:
        choice = Prompt.ask("Enter the number or your own value").strip()

        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(options):
                return options[index]
            elif allow_custom and index == len(options):
                return input("Enter your own value: ").strip()
            else:
                print("[bold red]Invalid choice, please try again.[/bold red]")
        else:
            if allow_custom:
                return choice
            else:
                print("[bold red]Invalid input, please try again.[/bold red]")

def form_download_data_command(timeframe, timerange):
    # Gérer les timeframes multiples en les joignant correctement avec des virgules
    if isinstance(timeframe, str) and " " in timeframe:
        timeframe = ",".join(timeframe.split())
    
    return (
        f"freqtrade download-data --config "
        f"{os.path.join(CONFIG_PATH, config_file_name)} "
        f"--timeframe {timeframe} --timerange {timerange}"
    )

def form_backtesting_command(strategy, timeframe, timerange):
    # Form the command for backtesting
    return (
        f"freqtrade backtesting --strategy {strategy} "
        f"--config {os.path.join(CONFIG_PATH, config_file_name)} "
        f"--timerange {timerange} --timeframe {timeframe}"
    )

def form_plot_profit_command(strategy, timeframe, pairs, timerange):
    # Form the command for plotting profit
    return (
        f"freqtrade plot-profit --strategy {strategy} "
        f"--config {os.path.join(CONFIG_PATH, config_file_name)} "
        f"--timeframe {timeframe} --pairs {pairs} "
        f"--timerange {timerange}"
    )

def form_hyperopt_command(strategy, loss_function, spaces,
                          timeframe, timerange, epochs):
    # Form the command for hyperopt
    return (
        f"freqtrade hyperopt --strategy {strategy} "
        f"--hyperopt-loss {loss_function} --spaces {spaces} "
        f"--timerange {timerange} -e {epochs} "
        f"--config {os.path.join(CONFIG_PATH, config_file_name)} "
        f"--timeframe {timeframe}"
    )

def shorten_filename(filename, max_length=180):
    # Split the filename into name and extension
    filename_without_extension, extension = os.path.splitext(filename)
    if len(filename_without_extension) > max_length:
        # Shorten the name, keeping a hash for uniqueness
        hash_digest = hashlib.sha256(
            filename_without_extension.encode()
        ).hexdigest()[:8]
        allowed_length = (max_length - len(extension) -
                          len(hash_digest) - 1)
        filename_without_extension = (
            f"{filename_without_extension[:allowed_length]}"
            f"_{hash_digest}"
        )
    return f"{filename_without_extension}{extension}"

def save_command_result(command_result, command_name,
                        tested_file_name, command):
    # Create a safe filename from the command
    safe_command = re.sub(r'[^\w\-_\. ]', '_', command)
    original_filename = (
        f"{command_name}_{tested_file_name}_{safe_command}"
    )
    
    # Apply the filename shortening function
    filename = shorten_filename(original_filename)
    save_path = os.path.join(RESULTS_PATH, filename)
    
    try:
        with open(save_path, 'w', encoding='utf-8') as file:
            file.write(command_result)
        print(f"[bold green]Result saved to file:[/bold green] {save_path}")
    except Exception as e:
        print(f"Error saving file: {e}")

def form_trade_command(strategy):
    # Form the command for trading
    return (
        f"freqtrade trade --strategy {strategy} "
        f"--config {os.path.join(CONFIG_PATH, config_file_name)}"
    )

def run_command(command):
    console.print(f"[bold blue]Exécution de la commande:[/bold blue] [yellow]{command}[/yellow]")
    try:
        process = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding='utf-8'  # Spécifier l'encodage explicitement
        )
        
        # Ajouter un timeout pour éviter les blocages
        command_output, _ = process.communicate(timeout=600)  # 10 minutes timeout
        console.print(command_output)
        
        args = shlex.split(command)
        strategy_name = 'general'
        if '--strategy' in args:
            strategy_index = args.index('--strategy') + 1
            strategy_name = args[strategy_index]
        
        return command_output, strategy_name
    except subprocess.TimeoutExpired:
        process.kill()
        console.print("[bold red]La commande a dépassé le délai d'attente (10 minutes)[/bold red]")
        return "", "general"
    except Exception as e:
        console.print(f"[bold red]Erreur lors de l'exécution de la commande '{command}':[/bold red] {e}")
        return "", "general"

# Get a list of strategy files
files = sorted([
    f for f in os.listdir(STRATEGY_PATH)
    if os.path.isfile(os.path.join(STRATEGY_PATH, f))
    and f.endswith('.py')
])

# Choose the function to run
function_choice = get_choice(
    ["Test Strategies", "Download Data",
     "Hyperopt", "Trade", "Plot"],
    "Select the function to run:"
)

# Get a list of configuration files
config_files = sorted([
    f for f in os.listdir(CONFIG_PATH)
    if os.path.isfile(os.path.join(CONFIG_PATH, f))
    and f.endswith('.json')
])

# Ask the user for the configuration file name
config_file_name = get_choice(
    config_files, "Select the configuration file:"
)

if function_choice == "Test Strategies":
    # Choose testing option
    test_option = get_choice(
        ["Test All Strategies",
         "Test Selected Strategy"],
        "Select an option:"
    )
    if test_option == "Test Selected Strategy":
        file_name_with_extension = get_choice(
            files, "Select a file:"
        )
        strategy_name = os.path.splitext(
            file_name_with_extension
        )[0]  # Remove .py extension
        timeframe_choice = get_choice(
            TIMEFRAMES, "Select timeframe:"
        )
        timerange_choice = get_choice(
            TIMERANGES, "Select timerange:"
        )

    elif test_option == "Test All Strategies":
        timeframe_choice = get_choice(
            TIMEFRAMES, "Select timeframe:"
        )
        timerange_choice = get_choice(
            TIMERANGES, "Select timerange:"
        )

elif function_choice == "Hyperopt":
    # Choose hyperopt option
    hyperopt_option = get_choice(
        ["Optimize All Strategies",
         "Optimize Selected Strategy"],
        "Select an option:"
    )
    if hyperopt_option == "Optimize Selected Strategy":
        file_name_with_extension = get_choice(
            files, "Select a file:"
        )
        strategy_name = os.path.splitext(
            file_name_with_extension
        )[0]  # Remove .py extension
        hyperopt_loss = get_choice(
            LOSS_FUNCTIONS, "Select loss function:"
        )
        spaces = get_choice(
            SPACES, "Select spaces:"
        )
        while True:
            epochs = input("Enter the number of epochs: ")
            if epochs.isdigit():
                break
            else:
                print("[bold red]Please enter a numeric value.[/bold red]")
        
        timeframe_choice = get_choice(
            TIMEFRAMES, "Select timeframe:"
        )
        timerange_choice = get_choice(
            TIMERANGES, "Select timerange:"
        )
    
    elif hyperopt_option == "Optimize All Strategies":
        hyperopt_loss = get_choice(
            LOSS_FUNCTIONS, "Select loss function:"
        )
        spaces = get_choice(
            SPACES, "Select spaces:"
        )
        timeframe_choice = get_choice(
            TIMEFRAMES, "Select timeframe:"
        )
        timerange_choice = get_choice(
            TIMERANGES, "Select timerange:"
        )
        while True:
            epochs = input("Enter the number of epochs: ")
            if epochs.isdigit():
                break
            else:
                print("[bold red]Please enter a numeric value.[/bold red]")

# Strategy files already filtered
strategy_files = files

# Form commands
commands = []

if function_choice == "Test Strategies":
    if test_option == "Test All Strategies":
        # Generate commands for all strategies
        commands = [
            form_backtesting_command(
                os.path.splitext(strategy_file)[0],
                timeframe_choice, timerange_choice
            )
            for strategy_file in strategy_files
        ]

        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=4
        ) as executor:
            future_to_command = {
                executor.submit(
                    run_command, cmd
                ): cmd for cmd in commands
            }
            for future in concurrent.futures.as_completed(
                future_to_command
            ):
                cmd = future_to_command[future]
                try:
                    # Set a timeout for each command
                    command_output, strategy_name = future.result(
                        timeout=300  # 5-minute timeout
                    )
                    # Save command results to file
                    save_command_result(
                        command_output, "Test Strategies",
                        strategy_name, cmd
                    )
                    print(f"[bold green]Command completed:[/bold green] {cmd}")
                except concurrent.futures.TimeoutError:
                    print(
                        f"Command exceeded time limit (5 minutes) "
                        f"and was skipped: {cmd}"
                    )
                except Exception as exc:
                    print(
                        f"Command generated an exception: {exc}. "
                        f"Command: {cmd}"
                    )

    elif test_option == "Test Selected Strategy":
        command = form_backtesting_command(
            strategy_name, timeframe_choice, timerange_choice
        )
        commands.append(command)

elif function_choice == "Download Data":
    timeframe_choice = get_choice(
        TIMEFRAMES + ["1m 5m 15m 30m 1h 4h 8h 1d",
                      "30m 1h 4h 8h 1d", "1m 5m 15m"],
        "Select timeframe:"
    )
    timerange_choice = get_choice(
        TIMERANGES, "Select timerange:"
    )
    command = form_download_data_command(
        timeframe_choice, timerange_choice
    )
    
    # Execute the command outside of thread pool
    command_output, _ = run_command(command)
    save_command_result(
        command_output, "Download Data", "general", command
    )

elif function_choice == "Trade":
    # Choose the strategy for trading
    strategy_file = get_choice(
        strategy_files, "Select strategy:"
    )
    strategy_name = os.path.splitext(
        strategy_file
    )[0]  # Get filename without extension

    command = form_trade_command(strategy_name)
    commands.append(command)
    
elif function_choice == "Hyperopt":
    if hyperopt_option == "Optimize All Strategies":
        for strategy_file in strategy_files:
            strategy_name = os.path.splitext(
                strategy_file
            )[0]  # Get filename without extension

            command = form_hyperopt_command(
                strategy_name, hyperopt_loss, spaces,
                timeframe_choice, timerange_choice, epochs
            )
            commands.append(command)
    elif hyperopt_option == "Optimize Selected Strategy":
        command = form_hyperopt_command(
            strategy_name, hyperopt_loss, spaces,
            timeframe_choice, timerange_choice, epochs
        )
        commands.append(command)

elif function_choice == "Plot":
    strategy_file = get_choice(
        strategy_files, "Select strategy:"
    )
    strategy_name = os.path.splitext(
        strategy_file
    )[0]  # Get filename without extension
    timeframe_choice = get_choice(
        TIMEFRAMES, "Select timeframe:"
    )
    pairs = input(
        "Enter the currency pair (e.g., LTC/USDT): "
    ).strip()
    timerange_choice = get_choice(
        TIMERANGES, "Select timerange:"
    )
    command = form_plot_profit_command(
        strategy_name, timeframe_choice, pairs, timerange_choice
    )
    commands.append(command)

# Execute commands
for cmd in commands:
    print(f"Executing command: {cmd}")
    try:
        process = subprocess.Popen(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        command_output, _ = process.communicate()
        print(command_output)
        
        args = shlex.split(cmd)
        if '--strategy' in args:
            strategy_index = args.index('--strategy') + 1
            strategy_name = args[strategy_index]
        else:
            strategy_name = 'general'
        
        save_command_result(
            command_output, function_choice, strategy_name, cmd
        )
        print(f"[bold green]Command completed:[/bold green] {cmd}")
    except Exception as e:
        print(f"Error executing command '{cmd}': {e}")

# Application finished