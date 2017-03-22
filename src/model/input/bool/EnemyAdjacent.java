package model.input.bool;

import model.Agent;
import model.Map;
import model.input.DecisionBoolean;

public class EnemyAdjacent extends DecisionBoolean {

	@Override
	public boolean decide(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		if (hasEnemy(agent.getPlayer(), x - 1, y, map)) {
			return true;
		}
		if (hasEnemy(agent.getPlayer(), x + 1, y, map)) {
			return true;
		}
		if (hasEnemy(agent.getPlayer(), x, y - 1, map)) {
			return true;
		}
		if (hasEnemy(agent.getPlayer(), x, y + 1, map)) {
			return true;
		}
		return false;
	}
	
	public String toString() {
		String output = Option.ENEMY_ADJACENT.toString();
		return output;
	}

}
