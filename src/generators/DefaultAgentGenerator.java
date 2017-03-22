package generators;

import model.Agent;
import model.Player;

public class DefaultAgentGenerator implements AgentGenerator {


	public Agent createAgent(Player player, int x, int y) {
		return new Agent(x, y, player, player.getAgentSpeed(), player.getAgentHealth(), player.getAgentPower(), player.getTrees().get(0), 0);
	}
}
