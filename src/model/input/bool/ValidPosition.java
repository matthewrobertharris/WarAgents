package model.input.bool;

import model.Agent;
import model.Map;
import model.XY;
import model.input.DecisionBoolean;
import model.input.GetPosition;

public class ValidPosition extends DecisionBoolean {

	private GetPosition position;

	public ValidPosition(GetPosition position) {
		setPosition(position);
	}

	public GetPosition getPosition() {
		return position;
	}

	public void setPosition(GetPosition position) {
		this.position = position;
	}

	/**
	 * This method checks allows null values (e.g. on the primary or secondary)
	 */
	@Override
	public boolean decide(Agent agent, Map map) throws Exception {
		try {
			XY position = getPosition().getPosition(agent, map);
			return position != null;
		}
		catch(Exception e) {
			return false;
		}
	}

}
