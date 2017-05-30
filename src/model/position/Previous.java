package model.position;

import model.Agent;
import model.Map;
import model.XY;
import model.input.GetPosition;

public class Previous extends GetPosition {

	@Override
	public XY getPosition(Agent agent, Map map) {
		return agent.getPreviousXY();
	}

	public String toString() {
		String output = Position.PREVIOUS.toString();
		return output;
	}

}
