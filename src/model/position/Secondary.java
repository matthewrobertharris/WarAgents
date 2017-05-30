package model.position;

import model.Agent;
import model.Map;
import model.XY;
import model.input.GetPosition;

public class Secondary extends GetPosition {

	@Override
	public XY getPosition(Agent agent, Map map) {
		XY secondary = agent.getSecondary();
		return secondary;
	}

	public String toString() {
		String output = Position.SECONDARY.toString();
		return output;
	}
	
}
