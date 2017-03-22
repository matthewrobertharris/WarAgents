package readers;

import java.util.ArrayList;
import java.util.List;

import model.Agent;
import model.Player;
import model.tree.Tree;

public class PlayerReaderImpl implements PlayerReader {

	private TreeReader treeReader;

	public PlayerReaderImpl(TreeReader treeReader) {
		setTreeReader(treeReader);
	}

	public TreeReader getTreeReader() {
		return treeReader;
	}

	public void setTreeReader(TreeReader treeReader) {
		this.treeReader = treeReader;
	}

	@Override
	public Player convertPlayer(String gameData, int maxAgents, int lineNumber) {
		String[] lines = gameData.split(System.lineSeparator());
		String[] values = lines[lineNumber].split(",");
		String name = values[0].split("=")[1];
		int speed = Integer.valueOf(values[1].split("=")[1]);
		int health = Integer.valueOf(values[2].split("=")[1]);
		int power = Integer.valueOf(values[3].split("=")[1]);
		int x = Integer.valueOf(values[4].split("=")[1]);
		int y = Integer.valueOf(values[5].split("=")[1]);
		List<Tree> trees = getTreeReader().convertTrees(gameData, lineNumber + 1);
		List<Agent> agents = new ArrayList<Agent>();
		Player player = new Player(x, y, name, health, speed, power, trees, maxAgents, agents);
		return player;
	}

	@Override
	public List<Player> convertPlayers(String gameData) {
		String[] lines = gameData.split(System.lineSeparator());
		int maxAgents = 1;
		List<Player> players = new ArrayList<Player>();
		for (int i = 0; i < lines.length; i++) {
			String[] values = lines[i].split("=");
			if (values[0].equals("maxAgents")) {
				maxAgents = Integer.valueOf(values[1]);
			}
		}

		for (int i = 0; i < lines.length; i++) {
			String[] values = lines[i].split("=");
			if (values[0].equals("name")) {
				Player player = convertPlayer(gameData, maxAgents, i);
				players.add(player);
			}

		}

		return players;
	}

}
