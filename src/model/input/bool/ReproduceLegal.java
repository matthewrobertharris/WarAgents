package model.input.bool;

import model.Agent;
import model.Map;
import model.input.DecisionBoolean;

public class ReproduceLegal extends DecisionBoolean {

	@Override
	public boolean decide(Agent agent, Map map) {
		if(agent.getHealth() >= 2) {
			if(agent.getPlayer().hasSpace()) {
				int x = agent.getX();
				int y = agent.getY();
				if(inBounds(x - 1, y, map) && !map.getTile(x - 1, y).isOccupied()) {
					return true;
				}
				if(inBounds(x + 1, y, map) && !map.getTile(x + 1, y).isOccupied()) {
					return true;
				}
				if(inBounds(x, y - 1, map) && !map.getTile(x, y - 1).isOccupied()) {
					return true;
				}
				if(inBounds(x, y + 1, map) && !map.getTile(x, y + 1).isOccupied()) {
					return true;
				}
			}
		}
		return false;
	}
	
	public String toString() {
		String output = Option.LEGAL_MOVE.toString();
		return output;
	}
}
