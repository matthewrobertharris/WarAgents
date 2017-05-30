package model.position;

import model.Agent;
import model.Map;
import model.XY;
import model.input.GetPosition;

public class Left extends GetPosition {

	@Override
	public XY getPosition(Agent agent, Map map) {
		int x = agent.getX() - 1;
		int y = agent.getY();
		if(inBounds(x, y, map)) {
			return new XY(x, y);
		}
		return null;
	}

	public String toString() {
		String output = Position.LEFT.toString();
		return output;
	}
	
}
