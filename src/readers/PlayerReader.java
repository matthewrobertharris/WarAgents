package readers;

import java.util.List;

import model.Player;

public interface PlayerReader {

	public Player convertPlayer(String agentData, int maxAgents, int lineNumber);
	public List<Player> convertPlayers(String gameData);
}
