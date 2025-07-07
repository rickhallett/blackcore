from blackcore.notion.client import NotionClient, save_config_to_file, console


def main():
    """
    Initializes the Notion client, discovers accessible databases,
    and saves them to a configuration file.
    """
    try:
        notion = NotionClient()
        databases = notion.discover_databases()
        if databases:
            save_config_to_file(databases)
            console.print(
                "\nPlease review the generated file and adjust settings like 'title_property' to match your schemas.",
                style="yellow",
            )
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}", style="red")


if __name__ == "__main__":
    main()
