package model;

import java.util.ArrayList;
import java.util.List;

import org.junit.Test;

import junit.framework.TestCase;
import model.output.Action;
import model.tree.Tree;

public class AgentTest extends TestCase {

	private Agent agent;

	@Override
	protected void setUp() {
		
	}
	
	@Test
	public void testConstructor() {
		int x = 2;
		int y = 1;
		String playerName = "playerTest";
		String treeName = "treeTest";
		int speed = 10;
		int maxHealth = 100;
		int power = 15;
		Tree tree = new Tree(treeName);
		List<Tree> trees = new ArrayList<Tree>();
		trees.add(tree);
		int maxAgents = 5;
		List<Agent> agents = new ArrayList<Agent>();		
		Player player = new Player(x, y, playerName, maxHealth, speed, power, trees, maxAgents, agents);
		agent = player.getCurrentAgents().get(0);
		
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		assertTrue(agent.getAction().toString() == "test");
		//assertTrue(agent.getSecondary() == "test");
	}

	@Test
	public void testGetPreviousXY() {
		fail();
	}

	@Test
	public void testGetPreviousAction() {
		fail();
	}

	@Test
	public void testPrimary() {
		XY primary;
		fail();
	}

	@Test
	public void testSecondary() {
		XY secondary;
		fail();
	}

	@Test
	public void testDeath() {
		int death;
	}

	@Test
	public void testActionHistory() {
		List<Action> actionHistory;
		fail();
	}

	@Test
	public void testBirth() {
		fail();
	}

	@Test
	public void testAddHistory(AgentHistory agentHistory) {
		fail();
	}

	@Test
	public void testHistory() {
		fail();
	}

	@Test
	public void testTree() {
		fail();
	}

	@Test
	public void testIdCount() {
		fail();
	}

	@Test
	public void testDirt() {
		fail();
	}

	@Test
	public void testFood() {
		fail();
	}

	@Test
	public void testSpeed() {
		fail();
	}

	@Test
	public void testHealth() {
		fail();
	}

	@Test
	public void testMaxHealth() {
		fail();
	}

	@Test
	public void testPower() {
		fail();
	}

	@Test
	public void testExp() {
		fail();
	}

	@Test
	public void testLevel() {
		fail();
	}

	@Test
	public void testPlayer() {
		fail();
	}

	@Test
	public void testAction() {
		fail();
	}

	@Test
	public void testUpdate() {
		Map map;
		fail();
	}

	@Test
	public void testToString() {
		fail();
	}
}
