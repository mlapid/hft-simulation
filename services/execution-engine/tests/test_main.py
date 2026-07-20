from execution_engine import main


def test_main_prints_greeting(capsys):
    main()
    captured = capsys.readouterr()
    assert captured.out == 'Hello from execution-engine!\n'