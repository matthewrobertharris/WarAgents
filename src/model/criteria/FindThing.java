package model.criteria;

import java.util.ArrayList;
import java.util.List;

import model.Agent;
import model.Map;
import model.Thing;
import model.XY;

public class FindThing implements Criteria {

	private Thing thing;

	public FindThing(Thing thing) {
		setThing(thing);
	}

	public Thing getThing() {
		return thing;
	}

	public void setThing(Thing thing) {
		this.thing = thing;
	}

	@Override
	public boolean isFinished(Map map) throws Exception {
		List<Agent> adjacent = new ArrayList<Agent>();
		int x = getThing().getX();
		int y = getThing().getY();
		XY left = new XY(x - 1, y);
		XY right = new XY(x + 1, y);
		XY up = new XY(x, y + 1);
		XY down = new XY(x, y - 1);
		if(map.isValid(left)) {
			adjacent.add(map.getTile(left).getAgent());
		}
		if(map.isValid(right)) {
			adjacent.add(map.getTile(right).getAgent());
		}
		if(map.isValid(up)) {
			adjacent.add(map.getTile(up).getAgent());
		}
		if(map.isValid(down)) {
			adjacent.add(map.getTile(down).getAgent());
		}
		Agent fastest = null;
		for(Agent agent : adjacent) {
			if(fastest == null) {
				fastest = agent;
			}
			else {
				if(agent.getSpeed() > fastest.getSpeed()) {
					fastest = agent;
				}
				else if(agent.getSpeed() == fastest.getSpeed()) {
					if(agent.getBirth() < fastest.getBirth()) {
						fastest = agent;
					}
				}
			}
		}
		if(fastest != null) {
			System.out.println("Player " + fastest.getPlayer().getName() + " wins!");
			return true;
		}
		return false;
	}

}
