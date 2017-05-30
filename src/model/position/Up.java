package model.position;

import model.Agent;
import model.Map;
import model.XY;
import model.input.GetPosition;

public class Up extends GetPosition {

	@Override
	public XY getPosition(Agent agent, Map map) {
		int x = agent.getX();
		int y = agent.getY() + 1;
		if(inBounds(x, y, map)) {
			return new XY(x, y);
		}
		return null;
	}

	public String toString() {
		String output = Position.UP.toString();
		return output;
	}
	
}
