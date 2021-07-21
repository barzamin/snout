import click
import matplotlib.pyplot as plt
from pprint import pprint
import rich
from rich.console import Console
from rich.columns import Columns
from rich.table import Table
from rich.rule import Rule
from rich.panel import Panel
from rich.text import Text
import serial
from . import parse_packet, SHTMeasurement, SCDMeasurement, PM25Measurement, Timestamp

@click.group()
def cli(): ...

@cli.group(name='serial')
@click.option('--serport', default='/dev/ttyACM1')
@click.pass_context
def gp_serial(ctx, serport):
    ctx.ensure_object(dict)
    ctx.obj['serport'] = serport


@cli.command()
def plot():
    packets = []
    with open('env.dat', 'rb') as f:
        while True:
            try:
                packets.append(parse_packet(f))
            except EOFError:
                break

    pprint(packets[-10:])
    ms = [p for p in packets if isinstance(p, SHTMeasurement)]
    temps = [p.temp for p in ms]
    rhs = [p.rh for p in ms]
    fig, ax1 = plt.subplots()
    ax1.set_ylabel('temp (°C)', color='r')
    ax2 = ax1.twinx()
    # ax2.set_ylabel('RH (%)', color='b')
    ax2.set_ylabel('CO2 (ppm)', color='b')

    ax1.plot(temps, color='r')
    ax2.plot(rhs, color='b')
    plt.show()

@gp_serial.command()
@click.pass_context
def packets(ctx):
    with serial.Serial(ctx.obj['serport']) as f:
        while True:
            rich.print(parse_packet(f))

def c_to_f(c):
    return 9/5 * c + 32

@gp_serial.command()
@click.pass_context
def mon(ctx):
    console = Console()
    with serial.Serial(ctx.obj['serport']) as f:
        time = 0
        while True:
            p = parse_packet(f)
            if isinstance(p, Timestamp):
                time = p.secs
                console.print(Rule(f'{time}', style='grey bold'))
            elif isinstance(p, SCDMeasurement):
                t = Text(f'''CO2:   {p.co2:0.2f}ppm
temp:  {p.temp:0.2f}°C ({c_to_f(p.temp):0.2f}°F)
humid: {p.rh:0.1f}%''')
                console.print(Panel(t))
            elif isinstance(p, SHTMeasurement):
                t = Text(f'''\
temp:  {p.temp:0.2f}°C ({c_to_f(p.temp):0.2f}°F)
humid: {p.rh:0.1f}%''')
                console.print(Panel(t))
            elif isinstance(p, PM25Measurement):
                t = Text.from_markup(f'''\
      [bold]pm2.5[/]  [bold]pm10[/]  [bold]pm100[/]
    ┌─────────────────────
[bold]env[/] │ {p.pm_std[25]:<5}  {p.pm_std[10]:<5} {p.pm_std[100]:<5}
[bold]std[/] │ {p.pm_env[25]:<5}  {p.pm_env[10]:<5} {p.pm_env[100]:<5}''')

                # table = Table('.3', '.5', '1.0', '2.5', '5.0', '10.0',
                #     show_header=True, header_style='bold')
                table = Table('size [µm]', 'count/0.1L', show_header=True, header_style='bold')
                for name, key in zip(['.3', '.5', '1.0', '2.5', '5.0', '10.0',], [3, 5, 10, 25, 50, 100]):
                    table.add_row(name, str(p.particle_count[key]))
                # table.add_row(f'{p.particle_count[3]}', f'{p.particle_count[5]}', f'{p.particle_count[10]}', f'{p.particle_count[25]}', f'{p.particle_count[50]}', f'{p.particle_count[100]}')

                columns = Columns((t, table,), equal=True, expand=True)
                console.print(Panel(columns))

@gp_serial.command()
@click.pass_context
def plot(ctx):
    import matplotlib.animation as animation
    with serial.Serial(ctx.obj['serport']) as f:
        fig, ax = plt.subplots()
        xd, yd = [], []
        ln, = plt.plot([], [], 'r')

        def packetgen():
            time = 0
            while True:
                p = parse_packet(f)
                if isinstance(p, Timestamp):
                    time = p.secs
                else:
                    yield time, p

        def update(frame):
            time, p = frame

            ax.set_xlim(min(xd, default=0)-10, max(xd, default=0)+10)
            ax.set_ylim(min(yd, default=0)-10, max(yd, default=0)+10)

            if isinstance(p, SCDMeasurement):
                xd.append(time)
                yd.append(p.co2)
                ln.set_data(xd, yd)

            return ln,

        def init():
            ln.set_data(xd, yd)
            return ln,

        ani = animation.FuncAnimation(fig, update, frames=packetgen, init_func=init)
        plt.show()
        # while True:
        #     p = parse_packet(f)
        #     if isinstance(p, Timestamp):
        #         time = p.secs

if __name__ == '__main__': cli()