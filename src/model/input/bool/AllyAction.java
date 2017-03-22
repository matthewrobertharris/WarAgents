package model.input.bool;

import model.Agent;
import model.Map;
import model.Tile;
import model.XY;
import model.input.DecisionBoolean;
import model.input.GetPosition;
import model.output.Action.Activity;

public class AllyAction extends DecisionBoolean {

	private GetPosition position;
	private Activity action;
	
	public AllyAction(GetPosition position, Activity action) {
		setPosition(position);
		setAction(action);
	}
	
	public AllyAction(GetPosition position, String action) {
		setPosition(position);
		setAction(Activity.valueOf(action));
	}

	public GetPosition getPosition() {
		return position;
	}

	public void setPosition(GetPosition position) {
		this.position = position;
	}

	public Activity getAction() {
		return action;
	}

	public void setAction(Activity action) {
		this.action = action;
	}

	@Override
	public boolean decide(Agent agent, Map map) throws Exception {
		XY position = getPosition().getPosition(agent, map);
		Tile tile = map.getTile(position);
		Agent ally = tile.getAgent();
		if(ally != null && ally.getPlayer().equals(agent.getPlayer())) {
			String a = ally.getAction().toString();
			return a.equals(agent.getAction().toString());
		}
		else {
			return false;
		}
	}
	
	public String toString() {
		String output = Option.ALLY_ACTION.toString();
		return output;
	}

}
