package readers;

import java.util.List;

import model.Player;

public interface ModeReader {

	public int readMode(List<Player> players, String gameData);
}
