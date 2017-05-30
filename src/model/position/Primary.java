package model.position;

import model.Agent;
import model.Map;
import model.XY;
import model.input.GetPosition;

public class Primary extends GetPosition {

	@Override
	public XY getPosition(Agent agent, Map map) {
		XY primary = agent.getPrimary();
		return primary;
	}

	public String toString() {
		String output = Position.PRIMARY.toString();
		return output;
	}
	
}
