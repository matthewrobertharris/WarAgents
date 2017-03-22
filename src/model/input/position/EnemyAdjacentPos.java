package model.input.position;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import model.Agent;
import model.Map;
import model.XY;
import model.input.DecisionPosition;

public class EnemyAdjacentPos extends DecisionPosition {

	@Override
	public XY decide(Agent agent, Map map) throws Exception {
		List<Integer> random = new ArrayList<Integer>();
		for(int i = 0; i < 4; i++) {
			random.add(i);
		}
		Random rnd = new Random();
		int x = agent.getX();
		int y = agent.getY();
		XY xy = new XY(x, y);
		Agent a = null;
		for(int i = 0; i < random.size(); i++) {
			switch(random.remove(rnd.nextInt(random.size()))) {
			case 0:
				a = checkAgent(x - 1, y, map);
				if(a != null && a.getPlayer().equals(agent.getPlayer())) {
					return new XY(x - 1, y);
				}
				break;
			case 1:
				a = checkAgent(x + 1, y, map);
				if(a != null && a.getPlayer().equals(agent.getPlayer())) {
					return new XY(x + 1, y);
				}
				break;
			case 2:
				a = checkAgent(x, y - 1, map);
				if(a != null && a.getPlayer().equals(agent.getPlayer())) {
					return new XY(x, y - 1);
				}
				break;
			case 3:
				a = checkAgent(x, y + 1, map);
				if(a != null && a.getPlayer().equals(agent.getPlayer())) {
					return new XY(x, y + 1);
				}
				break;
			}
		}
		return xy;
	}
	
	public String toString() {
		String output = Option.ENEMY_ADJACENT_POS.toString();
		return output;
	}
}
