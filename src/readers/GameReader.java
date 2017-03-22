package readers;

import main.Game;

public interface GameReader {

	public Game readGame(String file);
	public Game convertGame(String gameData);
}
