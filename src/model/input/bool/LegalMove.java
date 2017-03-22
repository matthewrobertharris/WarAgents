package model.input.bool;

import model.Agent;
import model.Map;
import model.input.DecisionBoolean;

public class LegalMove extends DecisionBoolean {

	@Override
	public boolean decide(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY();
		if (!occupied(x - 1, y, map)) {
			return true;
		}
		if (!occupied(x + 1, y, map)) {
			return true;
		}
		if (!occupied(x, y - 1, map)) {
			return true;
		}
		if (!occupied(x, y + 1, map)) {
			return true;
		}
		return false;
	}
	
	public String toString() {
		String output = Option.LEGAL_MOVE.toString();
		return output;
	}

}
