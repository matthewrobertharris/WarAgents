package model.input.getposition;

import model.Agent;
import model.Map;
import model.XY;
import model.input.GetPosition;

public class Current extends GetPosition {

	@Override
	public XY getPosition(Agent agent, Map map) {
		return agent.getCurrentPos();
	}

	public String toString() {
		String output = Position.CURRENT.toString();
		return output;
	}
	
}
