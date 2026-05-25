import typer

app = typer.Typer(
    name="ttcli",
    help="Minimal TickTick CLI",
)


@app.callback()
def callback() -> None:
    pass


if __name__ == "__main__":
    app()
