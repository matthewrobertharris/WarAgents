package generators;

import model.Agent;
import model.Player;

public interface AgentGenerator {

	public Agent createAgent(Player player, int x, int y);
	
}
