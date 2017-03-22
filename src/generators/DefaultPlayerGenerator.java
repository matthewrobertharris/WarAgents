package generators;

import java.util.ArrayList;
import java.util.List;

import model.Agent;
import model.Player;
import model.tree.Tree;

public class DefaultPlayerGenerator implements PlayerGenerator {

	public static final int AGENT_HEALTH = 100;
	public static final int AGENT_SPEED = 15;
	public static final int AGENT_POWER = 15;
	public static final int MAX_AGENTS = 15;
	
	@Override
	public Player generatePlayer(String name, List<Tree> trees) {
		return new Player(name, AGENT_HEALTH, AGENT_SPEED, AGENT_POWER, trees, MAX_AGENTS, new ArrayList<Agent>());
	}

	@Override
	public Player generatePlayer(String name, int agentHealth, int agentSpeed, int agentPower, List<Tree> trees) {
		return generatePlayer(name, trees);
	}

	@Override
	public Player generatePlayer(List<Tree> trees) {
		return generatePlayer("Test", AGENT_HEALTH, AGENT_SPEED, AGENT_POWER, trees);
	}


}
